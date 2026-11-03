from langchain.chains import LLMChain
from langchain_community.llms import CTransformers
from langchain_core.prompts import PromptTemplate


llm = CTransformers(
    model="zoltanctoth/orca_mini_3B-GGUF",
    model_file="orca-mini-3b.q4_0.gguf",
    model_type="llama",
    max_new_tokens=100,
)

prompt = PromptTemplate(
    template=(
        "### System:\n"
        "You are a helpful assistant. Answer briefly.\n\n"
        "### User:\n{question}\n\n"
        "### Response:\n"
    ),
    input_variables=["question"],
)

chain = LLMChain(llm=llm, prompt=prompt)
response = chain.invoke({"question": "What is LangChain?"})

print(response["text"])
