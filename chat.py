import chainlit as cl

from ctransformers import AutoModelForCausalLM


def get_prompt(instruction: str, history: list[str] = None) -> str:
    if history is None:
        history = []

    system = "You are a helpful assistant. you answer questions in a short and concise manner."
    prompt = f"### System:\n{system}\n\n### User:\n"
    if len(history) > 0:
        prompt += f"This is the conversation history: {', '.join(history)}. Now answer the question:"
    prompt += f"{instruction}\n\n### Response:\n"
    print(prompt)
    return prompt




@cl.on_message
async def on_message(message: cl.Message):
    message_history = cl.user_session.get("message_history") or []
    msg = cl.Message(content="")
    await msg.send()

    prompt = get_prompt(message.content, message_history)
    response = ""

    answer = ""
    for word in llm(prompt, stream=True):
        await msg.stream_token(word)
        answer += word

    await msg.update()
    message_history.append(response)

    message_history.extend([f"User: {message.content}", f"Assistant: {answer}"])
    cl.user_session.set("message_history", message_history)


@cl.on_chat_start
def on_chat_start():
    cl.user_session.set("message_history", [])
    global llm
    llm = AutoModelForCausalLM.from_pretrained(
        "zoltanctoth/orca_mini_3B-GGUF", model_file="orca-mini-3b.q4_0.gguf")


"""
history = []

question = "The capital of India is"

answer = ""
for word in llm(get_prompt(question), stream=True):
    print(word, end="", flush=True)
    answer += word

# Aquí actualiza history

question = "And what is the capital of Mexico?"

answer = ""
for word in llm(get_prompt(question, history), stream=True):
    print(word, end="", flush=True)
    answer += word


question = "The capital of India is"

for word in llm(get_prompt(question), stream=True):
    print(word, end="", flush=True)

    question = "And what is the capital of Mexico?"

for word in llm(get_prompt(question, history), stream=True):
    print(word, end="", flush=True)
    
    """
