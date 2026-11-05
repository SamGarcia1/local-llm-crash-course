"""Real pinned chain/callback/memory/worker bridge; mocked model and UI transport."""

import asyncio
import threading
import unittest
from contextvars import ContextVar
from types import SimpleNamespace
from unittest.mock import Mock, patch

from chainlit.context import context_var

import langchain_app as app


class SessionStore:
    def __init__(self):
        self.current = ContextVar("test_session")

    def get(self, key):
        return self.current.get().get(key)

    def set(self, key, value):
        self.current.get()[key] = value


class StreamingTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.context_token = context_var.set(
            SimpleNamespace(loop=asyncio.get_running_loop())
        )
        self.sessions = SessionStore()
        self.session = {}
        self.sessions.current.set(self.session)
        self.messages = []
        self.first_token = asyncio.Event()
        self.gates = []
        self.stream_error = False
        self.update_error = False
        self.update_interrupted = False
        owner = self

        class Message:
            def __init__(self, content):
                self.content = content
                self.streaming = False
                self.tokens = []
                self.sent = 0
                self.updated = 0
                owner.messages.append(self)

            async def send(self):
                self.sent += 1

            async def stream_token(self, token):
                self.streaming = True
                if owner.stream_error:
                    raise ConnectionError("Transport closed")
                self.tokens.append(token)
                self.content += token
                owner.first_token.set()

            async def update(self):
                self.updated += 1
                if owner.update_interrupted:
                    owner.update_interrupted = False
                    raise InterruptedError("Task stopped by user")
                if owner.update_error:
                    raise ConnectionError("Browser disconnected")
                self.streaming = False

        self.patches = [
            patch.object(app.cl, "Message", Message),
            patch.object(app.cl, "user_session", self.sessions),
        ]
        for item in self.patches:
            item.start()

    async def asyncTearDown(self):
        for gate in self.gates:
            gate.set()
        for item in reversed(self.patches):
            item.stop()
        context_var.reset(self.context_token)

    def chain(self, generate=None):
        if generate is None:
            generate = lambda *args, **kwargs: iter(["Hello", " world"])
        client = Mock(side_effect=generate)
        with patch("ctransformers.AutoModelForCausalLM.from_pretrained", return_value=client):
            chain = app.build_llm_chain()
        chain.verbose = False
        self.session["llm_chain"] = chain
        return chain, client

    def gated_chain(self):
        gate = threading.Event()
        self.gates.append(gate)

        def generate(*args, **kwargs):
            yield "Hello"
            if not gate.wait(5):
                raise TimeoutError("Test gate was not released")
            yield " world"

        chain, client = self.chain(generate)
        return chain, client, gate

    async def ask(self, text="Hi"):
        await app.on_message(SimpleNamespace(content=text))

    async def wait_token(self):
        await asyncio.wait_for(self.first_token.wait(), 3)

    async def test_tokens_arrive_before_completion_and_memory_saves_once(self):
        chain, _, gate = self.gated_chain()
        task = asyncio.create_task(self.ask())
        await self.wait_token()
        self.assertFalse(task.done())
        self.assertEqual(self.messages[0].content, "Hello")
        self.assertEqual(chain.memory.chat_memory.messages, [])
        gate.set()
        await asyncio.wait_for(task, 3)
        self.assertEqual(len(self.messages), 1)
        message = self.messages[0]
        self.assertEqual((message.sent, message.updated), (1, 1))
        self.assertEqual(message.tokens, ["Hello", " world"])
        self.assertEqual(message.content, "Hello world")
        self.assertFalse(message.streaming)
        self.assertEqual([m.content for m in chain.memory.chat_memory.messages], ["Hi", "Hello world"])

    async def test_final_answer_reconciles_without_duplicate(self):
        chain, _ = self.chain()

        def invoke(inputs, config):
            config["callbacks"][0].on_llm_new_token("draft")
            return {"text": "complete answer"}

        with patch.object(type(chain), "invoke", side_effect=invoke):
            await self.ask()
        self.assertEqual(len(self.messages), 1)
        self.assertEqual(self.messages[0].content, "complete answer")
        self.assertEqual(self.messages[0].updated, 1)

    async def test_followup_memory_and_reset_command(self):
        chain, client = self.chain()
        await self.ask("My name is Sam")
        await self.ask("What is my name?")
        self.assertIn("My name is Sam", client.call_args.args[0])
        self.assertIn("Hello world", client.call_args.args[0])
        calls = client.call_count
        await self.ask("  FORGET EVERYTHING  ")
        self.assertEqual(client.call_count, calls)
        self.assertEqual(chain.memory.chat_memory.messages, [])
        await self.ask("New question")
        self.assertNotIn("My name is Sam", client.call_args.args[0])

    async def test_reset_waits_for_generation_then_clears_memory(self):
        chain, _, gate = self.gated_chain()
        task = asyncio.create_task(self.ask())
        await self.wait_token()
        reset = asyncio.create_task(self.ask("forget everything"))
        await asyncio.sleep(0)
        self.assertFalse(reset.done())
        gate.set()
        await asyncio.wait_for(asyncio.gather(task, reset), 3)
        self.assertEqual(chain.memory.chat_memory.messages, [])

    async def test_generation_error_preserves_previous_memory(self):
        def broken(*args, **kwargs):
            yield "Partial"
            raise RuntimeError("Model failed")

        chain, _ = self.chain(broken)
        chain.memory.save_context({"question": "Earlier"}, {"text": "Answer"})
        with self.assertLogs("streaming", level="ERROR"):
            await self.ask()
        self.assertEqual([m.content for m in chain.memory.chat_memory.messages], ["Earlier", "Answer"])
        self.assertEqual(len(self.messages), 1)
        self.assertIn("Unable to complete", self.messages[0].content)
        self.assertFalse(self.messages[0].streaming)
        self.assertEqual(self.messages[0].updated, 1)

    async def test_callback_transport_error_is_not_swallowed(self):
        chain, _ = self.chain()
        self.stream_error = True
        with self.assertLogs("streaming", level="ERROR"):
            await self.ask()
        self.assertEqual(chain.memory.chat_memory.messages, [])
        self.assertFalse(self.messages[0].streaming)
        self.assertEqual(self.messages[0].updated, 1)

    async def test_disconnect_interrupts_and_failed_update_is_safe(self):
        chain, _, gate = self.gated_chain()
        task = asyncio.create_task(self.ask())
        await self.wait_token()
        await app.on_chat_end()
        self.update_error = True
        gate.set()
        with self.assertLogs("streaming", level="WARNING"):
            await asyncio.wait_for(task, 3)
        self.assertEqual(chain.memory.chat_memory.messages, [])
        self.assertFalse(self.messages[0].streaming)
        self.assertIn("interrupted", self.messages[0].content)
        self.assertIsNone(self.session["streaming_state"].active)
        self.update_error = False
        await self.ask("After reconnect")
        self.assertEqual(len(chain.memory.chat_memory.messages), 2)

    async def test_task_cancellation_holds_lock_until_worker_exits(self):
        chain, _, gate = self.gated_chain()
        task = asyncio.create_task(self.ask())
        await self.wait_token()
        task.cancel()
        await asyncio.sleep(0)
        reset = asyncio.create_task(self.ask("forget everything"))
        await asyncio.sleep(0)
        self.assertTrue(self.session["streaming_state"].lock.locked())
        self.assertFalse(reset.done())
        gate.set()
        with self.assertRaises(asyncio.CancelledError):
            await asyncio.wait_for(task, 3)
        await asyncio.wait_for(reset, 3)
        self.assertEqual(chain.memory.chat_memory.messages, [])
        self.assertFalse(self.messages[0].streaming)

    async def test_stop_cancels_queued_request(self):
        chain, client, gate = self.gated_chain()
        task = asyncio.create_task(self.ask())
        await self.wait_token()
        queued = asyncio.create_task(self.ask("Queued"))
        await asyncio.sleep(0)
        await app.on_stop()
        gate.set()
        await asyncio.wait_for(asyncio.gather(task, queued), 3)
        self.assertEqual(client.call_count, 1)
        self.assertEqual(chain.memory.chat_memory.messages, [])

    async def test_sessions_do_not_share_locks_or_memory(self):
        first_chain, _, gate = self.gated_chain()
        first = asyncio.create_task(self.ask("First user"))
        await self.wait_token()
        self.session = {}
        self.sessions.current.set(self.session)
        second_chain, _ = self.chain()
        await asyncio.wait_for(self.ask("Second user"), 3)
        self.assertFalse(first.done())
        self.assertEqual(first_chain.memory.chat_memory.messages, [])
        self.assertEqual(second_chain.memory.chat_memory.messages[0].content, "Second user")
        gate.set()
        await asyncio.wait_for(first, 3)
        self.assertEqual(first_chain.memory.chat_memory.messages[0].content, "First user")

    async def test_unavailable_model_behavior_is_unchanged(self):
        await self.ask()
        self.assertEqual(len(self.messages), 1)
        self.assertEqual(self.messages[0].content, "The model is unavailable right now. Sorry.")
        self.assertEqual(self.messages[0].sent, 1)
        self.assertNotIn("streaming_state", self.session)

    async def test_disconnect_at_memory_commit_rolls_back_only_current_turn(self):
        chain, _ = self.chain()
        chain.memory.save_context({"question": "Earlier"}, {"text": "Answer"})
        original_save = type(chain.memory).save_context

        def save_then_disconnect(memory, inputs, outputs):
            original_save(memory, inputs, outputs)
            self.session["streaming_state"].interrupt()

        with patch.object(type(chain.memory), "save_context", save_then_disconnect):
            await self.ask()
        self.assertEqual([m.content for m in chain.memory.chat_memory.messages], ["Earlier", "Answer"])
        self.assertIn("interrupted", self.messages[0].content)
        self.assertFalse(self.messages[0].streaming)

    async def test_empty_generation_finalizes_message(self):
        chain, _ = self.chain(lambda *args, **kwargs: iter([]))
        await self.ask()
        self.assertEqual(self.messages[0].updated, 1)
        self.assertFalse(self.messages[0].streaming)
        self.assertEqual(chain.memory.chat_memory.messages[-1].content, "")

    async def test_chainlit_stop_flag_does_not_prevent_final_update(self):
        chain, _, gate = self.gated_chain()
        task = asyncio.create_task(self.ask())
        await self.wait_token()
        await app.on_stop()
        self.update_interrupted = True
        gate.set()
        await asyncio.wait_for(task, 3)
        self.assertEqual(self.messages[0].updated, 2)
        self.assertFalse(self.messages[0].streaming)
        self.assertEqual(chain.memory.chat_memory.messages, [])

    async def test_final_delivery_failure_keeps_complete_successful_memory(self):
        chain, _ = self.chain()
        self.update_error = True
        with self.assertLogs("streaming", level="WARNING"):
            await self.ask()
        self.assertEqual(len(self.messages), 1)
        self.assertFalse(self.messages[0].streaming)
        self.assertEqual(chain.memory.chat_memory.messages[-1].content, "Hello world")
