"""Single-message streaming while LangChain retains ownership of memory."""

import asyncio
import logging
from dataclasses import dataclass, field
from threading import Event

import chainlit as cl
from langchain_core.callbacks import BaseCallbackHandler


logger = logging.getLogger(__name__)


class MessageStream(BaseCallbackHandler):
    # LangChain normally logs callback errors and continues generating.
    raise_error = True

    def __init__(self, message):
        self.message = message
        self.stopped = Event()

    def check_stopped(self):
        if self.stopped.is_set():
            raise InterruptedError("Response interrupted")

    def on_llm_new_token(self, token, **kwargs):
        self.check_stopped()
        cl.run_sync(self.message.stream_token(token))

    def on_llm_end(self, response, **kwargs):
        # Also catch a disconnect after the last token, before memory is saved.
        self.check_stopped()


@dataclass
class StreamingSession:
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    active: MessageStream | None = None
    generation: int = 0

    def interrupt(self):
        self.generation += 1
        if self.active is not None:
            self.active.stopped.set()


async def wait_for_worker(worker, stream):
    try:
        return await asyncio.shield(worker)
    except asyncio.CancelledError:
        stream.stopped.set()
        # A cancelled coroutine cannot release the session lock while the native
        # worker can still modify memory. Cancellation is cooperative per token.
        while not worker.done():
            try:
                await asyncio.shield(worker)
            except asyncio.CancelledError:
                continue
            except Exception:
                break
        if not worker.cancelled():
            worker.exception()  # Retrieve any worker exception before re-raising.
        raise


async def stream_response(chain, question, state):
    """Caller holds state.lock, including throughout cancellation cleanup."""
    message = cl.Message(content="")
    stream = MessageStream(message)
    state.active = stream
    history = list(chain.memory.chat_memory.messages)
    succeeded = False
    try:
        await message.send()
        stream.check_stopped()
        worker = asyncio.create_task(
            cl.make_async(chain.invoke)(
                {"question": question}, config={"callbacks": [stream]}
            )
        )
        response = await wait_for_worker(worker, stream)
        stream.check_stopped()
        message.content = response.get("text", str(response))
        succeeded = True
    except (InterruptedError, asyncio.CancelledError) as exc:
        stream.stopped.set()
        message.content += "\n\n[Response interrupted. Please try again.]"
        if isinstance(exc, asyncio.CancelledError):
            raise
    except Exception:
        logger.exception("Alfred response failed")
        message.content += "\n\n[Unable to complete this response. Please try again.]"
    finally:
        if not succeeded:
            # LangChain saves complete turns itself. Roll back only this failed
            # turn, including a disconnect racing with its final memory write.
            chain.memory.chat_memory.messages = history
        state.active = None
        message.streaming = False
        try:
            try:
                await message.update()
            except InterruptedError:
                # Chainlit 1.0.200 consumes its Stop flag on the next emission.
                await message.update()
        except Exception:
            # A disconnected browser cannot receive the final update; never
            # create a second answer or let transport failure corrupt memory.
            logger.warning("Could not deliver final response update", exc_info=True)
