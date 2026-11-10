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
conversion or second copy of the symbol is needed. The legacy `public/favicon.png` is now a transparent 256×256 derivative of
Signal. `/public/favicon.png` serves that PNG; `/favicon` and `/favicon.ico`
serve the original SVG. All three use `Cache-Control: no-store`. The document
explicitly links `/favicon`; `/favicon.ico` is a compatibility fallback.

Chainlit's native header image requests `/logo?theme=dark` or `/logo?theme=light`.
Both routes now serve `public/alfred-wordmark.svg` directly as `image/svg+xml`,
with `Cache-Control: no-store`. No CSS content replacement or crop is needed.
The intrinsic SVG dimensions keep the native 25px header image box, padding,
and navigation gap. Chainlit shares this endpoint with its login screen, which
therefore also displays the wordmark; the Signal avatar uses its separate URL. The outlined lettering uses Cormorant
Garamond Medium (500), ivory `#E6E1D5`, a 20px em, and 0.03em tracking. Its width
is 76.5px. The SVG contains glyph paths so no runtime font download is needed.
The font source is Google Fonts' `ofl/cormorantgaramond/CormorantGaramond[wght].ttf`
(instantiated at weight 500); its SIL Open Font License is included alongside
the asset. Manrope remains the interface font. The dark background is `#171816`.
The existing Pulse styling and animation are unchanged.

Verify in Codespaces after fully stopping and restarting the server (Ctrl-C,
then launch again). Chainlit's `-w` reloads application modules but retains the
installed ASGI middleware instance. Its registration guard intentionally avoids
duplicates, so editing `branding.py` requires a process restart. A page refresh
or watch-mode reload alone cannot replace that middleware.

1. Run `python -m unittest discover -s tests -v`, then
   `python -m chainlit run langchain_app.py --host 0.0.0.0 --port 8000 -w`.
2. At desktop width, confirm the header shows only the ivory ALFRED wordmark;
   check both themes. Confirm no clipping or navigation displacement beyond
   the intended wordmark width. Chainlit's native narrow-screen header hiding
   remains unchanged. The login screen also uses the shared wordmark endpoint.
3. Start a new chat and confirm Signal appears beside Alfred's welcome message,
   streamed answer, reset confirmation, and unavailable-model message. The user
   avatar should remain unchanged. Chainlit 1.0.200 uses a native 26px avatar;
   also preview the SVG at 32px and 40px without changing its geometry.
4. Inspect the document's `<link rel="icon" href="/favicon">`. In Network,
   verify `/favicon` returns 200, `Content-Type: image/svg+xml`, and
   `Cache-Control: no-store`; its bytes must equal `/public/alfred-signal.svg`.
   Do the same for both `/logo?theme=dark` and `/logo?theme=light`, comparing
   them to `/public/alfred-wordmark.svg`. Open the header's exact `currentSrc`
   to confirm the endpoint itself serves the new artwork. Check the tab icon in
   a fresh browser tab/profile if the browser retains an older favicon entry.
5. Send a prompt, observe Pulse then streaming, press Stop, send a follow-up,
   and test `forget everything`.

Validation: all 20 mocked-inference/configuration/branding tests pass on Python
3.11 with Chainlit 1.0.200 and LangChain 0.1.16. Regression checks cover actual
SVG bytes, both logo themes, favicon, GET/HEAD, MIME type, no-store headers and
conditional requests. The actual local Chainlit frontend (inference disabled)
was checked in Chromium: header renders the wordmark in both themes at 25px,
Signal avatar remains visible, and the document favicon link targets /favicon.
Live HTTP responses for that link and both logo themes returned the exact SVG
bytes with image/svg+xml and no-store. Codespaces inference and cross-browser
checks remain manual. The approved ivory wordmark has low contrast on the
native light theme; its color was not changed. Signal's 1.9-unit strokes remain
subtle at favicon size. Chainlit's native generic logo alt text and narrow-screen
logo hiding remain unchanged.

The previous CSS replacement only changed the image's presentation while
`/logo` still served the old PNG. The simplified preview did
not establish why the CSS failed in Codespaces; direct endpoint delivery removes
that dependency. No favicon response defect was reproduced after a clean start.
An existing watch-mode middleware instance or a browser favicon cache may retain
older branding; a process restart is required for middleware changes.

Favicon PNG generation: rasterize the unchanged `alfred-signal.svg` with Sharp
(libvips SVG renderer) at density 576 (1024×1024), then resize to 256×256 using
Lanczos3 and encode as RGBA PNG. This is build-time tooling only; no application
dependency is added. Preserve the SVG viewBox and transparency, including its
brass strokes and ivory center. Regenerate the PNG whenever the source changes.
The legacy PNG previously contained the framed A, while the canonical /favicon
already served Signal. This asset inconsistency is fixed; the user's persistent
tab icon could also reflect an older running middleware instance or browser
favicon cache, which cannot be conclusively diagnosed without that browser.


### Alfred 0.5 — Native voice input MVP

In a supported Chrome browser, use the microphone beside the composer, allow
microphone access, and speak. Press the recording Stop control when finished
(or let the native silence timeout end listening). **Review and edit the text
in the composer, then press Send.** Recognition appends text to the current
composer draft, so clear an unwanted draft before dictating. Nothing is submitted
automatically. The submitted transcript is an ordinary user message: it uses the
same Orca Mini chain, streaming, session memory, generation Stop, and
`forget everything` command as typed text.

Setup uses the existing requirements only. Native recognition is enabled in
`.chainlit/config.toml` under `[features.speech_to_text]`, with language `en-US`.
Change that BCP-47 language tag if needed and restart the server. No Python STT
package, API key, external account, GPU, custom JavaScript, or TTS is introduced.
The native microphone/recording-stop control is retained; custom Signal states
and animations are deferred. The Pulse still indicates response generation.

**Privacy and compatibility:** recognition runs through the browser's Web Speech
API, not Alfred's local LLM. Chrome may send audio to its speech-recognition
service, so voice input is not guaranteed local, offline, or available on every
Chrome platform. Network access and browser/organization policies can affect it.
Avoid dictating sensitive information unless you accept the browser service's
privacy behavior. Alfred's Python application receives the submitted text, not
recorded audio. Text chat remains available regardless of recognition support.

Chainlit 1.0.200 hides the microphone when the browser reports no speech-recognition
support. Its native control has limited permission and transcription error
feedback; Alfred cannot add reliable recovery messages without replacing that
frontend. If the control appears stuck, press recording Stop, check permissions,
and reload if needed. Denied permission: allow the microphone in Chrome's site
settings and the operating system's privacy settings, then retry. Empty or failed
recognition: no new transcript is available; stop recording, check microphone,
network and language, and retry or type. Clear any partial/incorrect text before
sending. Recording Stop and response-generation Stop are separate controls.

#### Codespaces verification

1. Check out `feature/alfred-0.5-voice-input`. Install the existing
   `requirements.txt` if necessary. From the repository root, run:
   ```sh
   python -m unittest discover -s tests -v
   python -m chainlit run langchain_app.py --host 0.0.0.0 --port 8000 -w
   ```
2. Open the forwarded port's **HTTPS URL in a full Chrome tab**, rather than an
   embedded preview. Allow microphone access for that Codespaces origin. Different
   Codespaces URLs may need separate permission grants.
3. Start a chat and verify the ALFRED header, Signal avatar/favicon, and text chat.
   Dictate “My name is Sam,” stop recording, and confirm text appears in the
   composer without generating a response. Correct it if necessary, then Send.
4. Confirm The Pulse followed by a single streamed answer. Type “What is my name?”
   in the same chat to verify shared memory. Dictate a follow-up and submit it too.
5. Stop a generated response, then send another message. Submit `forget everything`
   (typed or dictated, correcting recognition/punctuation to that exact command)
   and confirm the existing reset behavior.
6. Deny microphone permission, try silence, and simulate unavailable recognition
   (for example, a browser without Web Speech support). Confirm typed chat still
   works. Restore permission and retry. Check that failed recognition does not
   automatically submit partial text or overwrite an existing draft.

Automated validation covers the native speech settings through Chainlit's own
parser/serialization plus the existing branding, streaming, memory, cancellation,
and error tests. Microphone permission prompts, browser recognition accuracy,
service outages and real Codespaces audio require the manual checks above; no
mocked test is claimed to validate actual speech recognition.
