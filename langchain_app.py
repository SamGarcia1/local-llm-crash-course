import chainlit as cl
from langchain.chains import LLMChain
from langchain.memory import ConversationBufferMemory
from langchain_community.llms import CTransformers
from langchain_core.prompts import PromptTemplate

MODEL_REPO = "zoltanctoth/orca_mini_3B-GGUF"
MODEL_FILE = "orca-mini-3b.q4_0.gguf"
MODEL_TYPE = "llama"


def get_prompt_template() -> PromptTemplate:
    return PromptTemplate(
        input_variables=["history", "question"],
        template=(
            "### System:\n"
            "You are Alfred, an AI assistant that gives helpful answers. "
            "Answer questions in a short and concise way. "
            "Take this context into account when answering the question:\n"
            "{history}\n\n"
            "### User:\n"
            "{question}\n\n"
            "### Response:\n"
        ),
    )


def build_llm_chain() -> LLMChain:
    llm = CTransformers(
        model=MODEL_REPO,
        model_file=MODEL_FILE,
        model_type=MODEL_TYPE,
        config={"max_new_tokens": 128, "temperature": 0.7},
    )
    memory = ConversationBufferMemory(memory_key="history")
    return LLMChain(llm=llm, prompt=get_prompt_template(), memory=memory, verbose=True)


@cl.on_chat_start
async def on_chat_start():
    try:
        llm_chain = build_llm_chain()
        cl.user_session.set("llm_chain", llm_chain)
        await cl.Message(content="Alfred is running with LangChain!").send()
    except Exception as exc:  # pragma: no cover - app-side safeguard
        cl.user_session.set("llm_chain", None)
        await cl.Message(
            content=(
                "The local model could not be loaded. "
                f"This usually means the model isn't downloaded yet. Details: {exc}"
            )
        ).send()


@cl.on_message
async def on_message(message: cl.Message):
    llm_chain = cl.user_session.get("llm_chain")

    if llm_chain is None:
        await cl.Message(content="The model is unavailable right now. Sorry.").send()
        return

    if message.content.strip().lower() == "forget everything":
        llm_chain.memory.clear()
        await cl.Message(
            content="Uh oh, I've just forgotten our conversation history"
        ).send()
        return

    response = await cl.make_async(llm_chain.invoke)({"question": message.content})
    answer = response.get("text", str(response))
    await cl.Message(content=answer).send()
