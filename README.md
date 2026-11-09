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
clear it. Responses stream progressively into one message, which is finalized
with the complete returned answer.

## Alfred 0.2 — Streaming responses

A per-request LangChain callback forwards each generated text chunk to the same
Chainlit message. Inference still runs through `cl.make_async` in a worker thread;
`cl.run_sync` delivers tokens on Chainlit's event loop. Model, generation settings,
branding and dependencies are unchanged.

LangChain saves the complete successful turn to session memory once. Partial
tokens and error notices are not added to memory. A per-session lock serializes
generation and `forget everything`; a reset submitted during generation waits
for that turn to finish and then clears memory. Different sessions remain independent.

Stop or browser disconnect signals cooperative cancellation. Requests already
queued in that session are discarded; a new request after reconnect can proceed.
The worker must exit before the lock is released, and failed/interrupted turns
are rolled back without losing earlier successful turns. Errors finalize the same
message with a short notice, without creating another answer.

### Verify in Codespaces

Use Python 3.11 and the existing pinned requirements. Run:

```bash
python -m unittest discover -s tests -v
python -m chainlit run langchain_app.py --host 0.0.0.0 --port 8000 -w
```

Open forwarded port 8000 in a standalone browser tab and check:

1. Ask for a short explanation. Text should appear progressively in one message;
   completion must not produce a duplicate answer or a lingering streaming cursor.
2. Say `My name is Sam`, then ask `What is my name?` to exercise follow-up context.
3. Send `forget everything` and confirm the reset acknowledgement. Repeat during
   generation if the UI permits: reset should finish after the active turn, and
   a subsequent prompt must not contain the old conversation.
4. Stop a response mid-generation, then ask another question. The interrupted
   turn should not enter memory, and the next response should stream normally.
5. Close/reload the browser during generation, reopen the app, and submit another
   question. No old response should keep streaming into the new one. A reconnect
   within the retained session may preserve earlier completed turns; a new session
   starts fresh. There is no partial-stream replay or persistent history feature.
6. Check the header, favicon, styling and unavailable-model message remain unchanged.

Automated tests mock native inference and the UI transport while exercising the
real pinned LangChain callback, memory, worker-thread and `cl.run_sync` bridge.
They cover incremental delivery, completion, reset races, errors, cancellation,
disconnects and session isolation without downloading model weights.

Streaming does not shorten prompt evaluation or model loading. Each token adds a
UI emission; measure real latency on Codespaces. Cancellation cannot forcibly stop
a native call already computing a token: cleanup and queued requests may wait for
that call to return. If the browser has disconnected, final UI delivery is best
effort; server-side streaming state is cleared, but the closed browser cannot be
updated. A complete successful inference remains in memory if only its final UI
update fails. The existing context-window limit and unbounded history are unchanged.

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

## Branding endpoints (Chainlit 1.0.200)

Chainlit's header requests `/logo?theme=dark` or `/logo?theme=light`;
its HTML requests `/favicon`. These are separate from `/public/...`.
The stock handlers search under the working directory captured at Chainlit
import time (`APP_ROOT`) and use the first matching filename, falling back to
bundled Chainlit assets. The filenames already in this repository are supported;
no additional TOML option or different asset directory is required.

Alfred installs a small branding middleware for these two paths only. It serves
the exact PNG files from `public/` beside `branding.py`, independently of
Chainlit's captured root or other matching extensions. Responses use
`Cache-Control: no-store`; missing files return 404 instead of silently showing
Chainlit branding. All other requests, including chat and WebSockets, pass through.

After pulling this branch in Codespaces, stop the existing process and restart
Alfred from the repository root. Open the forwarded port in a standalone tab.
Run the focused check with:

```bash
python -m unittest discover -s tests -p test_branding.py -v
curl -fsS -D /tmp/alfred-logo.headers 'http://localhost:8000/logo?theme=dark' -o /tmp/alfred-logo.png
sha256sum /tmp/alfred-logo.png public/logo_dark.png
curl -fsS http://localhost:8000/favicon -o /tmp/alfred-favicon.png
sha256sum /tmp/alfred-favicon.png public/favicon.png
```

Each hash pair must match. The response headers should include `image/png` and
`Cache-Control: no-store`. Also check `/logo?theme=light` and refresh the app tab.
The separate Chainlit watermark below the composer is bundled SVG artwork and
is not changed by these endpoints.

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

### Alfred 0.4 visual identity

`public/alfred-signal.svg` is the approved, unmodified Signal Technical source.
The assistant avatar references it directly through Chainlit's `Avatar` API;
`branding.py` serves the same bytes at `/favicon` with `image/svg+xml`. No PNG
conversion or second copy of the symbol is needed. Existing PNGs are retained
for legacy logo routes; the old favicon PNG is no longer used by `/favicon`.

The header alone displays `public/alfred-wordmark.svg` through a scoped CSS image
replacement. This replaces the temporary crop and keeps the native 25px header
image box, padding, and navigation gap. The outlined lettering uses Cormorant
Garamond Medium (500), ivory `#E6E1D5`, a 20px em, and 0.03em tracking. Its width
is 76.5px. The SVG contains glyph paths so no runtime font download is needed.
The font source is Google Fonts' `ofl/cormorantgaramond/CormorantGaramond[wght].ttf`
(instantiated at weight 500); its SIL Open Font License is included alongside
the asset. Manrope remains the interface font. The dark background is `#171816`.
The existing Pulse styling and animation are unchanged.

Verify in Codespaces after restarting the server:

1. Run `python -m unittest discover -s tests -v`, then
   `python -m chainlit run langchain_app.py --host 0.0.0.0 --port 8000 -w`.
2. At desktop width, confirm the header shows only the ivory ALFRED wordmark;
   check both themes. Confirm no clipping or navigation displacement beyond
   the intended wordmark width. Chainlit's native narrow-screen header hiding
   remains unchanged. Login logo rendering is not changed.
3. Start a new chat and confirm Signal appears beside Alfred's welcome message,
   streamed answer, reset confirmation, and unavailable-model message. The user
   avatar should remain unchanged. Chainlit 1.0.200 uses a native 26px avatar;
   also preview the SVG at 32px and 40px without changing its geometry.
4. Open `/favicon` and compare it with `/public/alfred-signal.svg`. Check the tab
   icon in a fresh browser tab/profile if the browser retains the old favicon.
5. Send a prompt, observe Pulse then streaming, press Stop, send a follow-up,
   and test `forget everything`.

Validation: all 20 mocked-inference/configuration/branding tests pass on Python
3.11 with Chainlit 1.0.200 and LangChain 0.1.16. A Chromium browser fixture checked
the 25px header box, 26/32/40px avatar boxes, and 16/32px favicon sizes with the
actual assets and stylesheet. Live Codespaces inference and cross-browser
checks remain manual. Signal's original 1.9-unit strokes become subpixel at
small sizes, so its details are subtle at 16px; no thickening was applied.
CSS image replacement retains Chainlit's native generic `logo` alt text and
underlying PNG `src`; the dedicated wordmark is the rendered header content.
