# Alfred

Alfred's primary application is `langchain_app.py`: Chainlit with LangChain
conversation memory and Orca Mini 3B (`orca-mini-3b.q4_0.gguf`). `chat.py` and
`solutions/` remain learning examples.

## Run Alfred

Use Python 3.11, matching the devcontainer. From the repository root:

```bash
python -m pip install -r requirements.txt
python -m chainlit run langchain_app.py -w
```

In Codespaces, dependencies are installed by the devcontainer setup; open the
forwarded port 8000 after launching. The first chat may download the model from
Hugging Face and requires network access and enough memory to load it.

Generation uses the pinned CTransformers wrapper's `config` dictionary with
`max_new_tokens=128` and `temperature=0.7`. This is an output ceiling, not a target response length.
Conversation memory lasts for the current session; send `forget everything` to
clear it. Responses are displayed after generation completes.

## Baseline checks

Run from the repository root after installing the pinned requirements:

```bash
python -m unittest discover -s tests -v
```

These checks parse the real TOML and construct the real LangChain chain with only
the native model loader mocked. They verify generation settings reach the loader,
conversation history reaches subsequent prompts, and memory can be cleared.
They do not download model weights or verify native inference.

In Codespaces, also launch Alfred, confirm the startup message, ask a question,
ask a follow-up using prior context, then send `forget everything` and check a new
conversation. Verify the Wayne Manor styling still loads. Model startup, native
inference, browser behavior, and model-level recall require this manual smoke test.

# The Local LLM Crash Course - Build Your Own GPT in 2 hours!
This is the courseware and Codespace for the [The Local LLM Crash Course - Build Your Own GPT in 2 hours](https://www.udemy.com/course/the-local-llm-crash-course-build-a-hugging-face-ai-chatbot/?referralCode=EAD6017AA0001257DD9A)! Have fun with the course and use the Q&A if you run into any issues!

# Course Resources

### Codespaces Pricing and Free Credits
https://docs.github.com/en/billing/managing-billing-for-github-codespaces/about-billing-for-github-codespaces

### Hugging Face
* The Orca Model's Model Card: https://huggingface.co/zoltanctoth/orca_mini_3B-GGUF

###  Installing `ctransformers` and Chainlit
Just for reference. Remember, you don't need to do this as it's pre-installed in your Codespace.
```
pip install ctransformers chainlit
```

## The Open Orca Dataset
The dataset on Hugging Face: https://huggingface.co/datasets/Open-Orca/OpenOrca

## Chainlit and Streamlit
 * Chainlit: https://docs.chainlit.io/get-started/overview
 * Streamlit: https://streamlit.io/

## LangChain

### Installation
```
pip install langchain langchain-community
```

