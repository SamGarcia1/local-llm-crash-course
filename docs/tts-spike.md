# Alfred 0.6 — TTS technical spike

## Recommendation

Use browser SpeechSynthesis for a manual first experiment, with no application
STT/TTS dependencies, paid services, or model changes. The isolated page at
`/public/tts-spike.html` accepts a pasted completed answer. Speak is the only
entry point for audio. It neither reads nor modifies Chainlit's DOM, socket,
conversation, or memory. Native 0.5 dictation remains unchanged.

For eventual integrated voice conversation, maintain a frontend extension/build
against the pinned Chainlit source. Use React state and typed message events,
not MutationObserver, CSS selectors, or inferred transcript text. Chainlit
1.0.200 supports custom CSS/fonts and Python Actions/ChatSettings, but no custom
JavaScript setting or browser TTS action handler. Python Actions alone cannot
execute SpeechSynthesis on the user's device. Its Audio element plays audio
files; it is not a SpeechSynthesis bridge. A separate custom frontend is possible
but is a larger deployment/maintenance commitment, not part of this spike.

The native speech button appends recognition output to the same composer value
as typing. The submitted message carries no authoritative modality. A backend
ChatSettings toggle can express consent but cannot prove that a particular
message was dictated. To guarantee typed responses stay silent, future frontend
work must mark every submission with explicit provenance (typed/voice/mixed),
use a per-turn voice opt-in for ambiguous/edited input, and default to silent.
A global Voice Mode toggle alone must not cause every response to be spoken.

Capture voice eligibility and request ID at submission, not at answer completion.
The existing `stream_response` reconciles returned text and calls message.update;
that update also occurs on interrupted/error paths, so streaming=false alone is
not a success signal. Add an explicit correlated successful-completion event in
a future integration. Continue streaming text normally; queue speech once, only
for the complete successful eligible response. Do not speak raw tokens or error
suffixes. Keep one generation ID for speech; cancel on new user submission,
response Stop, reset, mode-off, disconnect, page exit and replacement speech.
Ignore late callbacks/events from cancelled generations. Memory remains owned
by the existing pipeline, never by TTS. Automatic mode is NOT implemented here.

## Browser behavior and limits

SpeechSynthesis provides getVoices, speak, cancel and voiceschanged. Voice lists
can arrive asynchronously; the prototype refreshes them without starting audio.
Voices are OS/browser dependent; localService distinguishes local from remote
services. The default voice may be remote. Voice quality, latency and language
support need listening tests on the actual device. No voice/model is downloaded
by Alfred, and no text is sent by the prototype itself except through the browser
speech engine chosen by the user. Remote engines may transmit text externally.

Treat user activation as required: Speak calls the API directly in a click
handler. Chrome restricts speech without activation; other browsers and embedded
frames may differ. A future toggle click does not guarantee that speech after a
long asynchronous inference will be permitted everywhere. Handle not-allowed and
offer a manual Speak fallback. Use a full HTTPS Codespaces tab, not an iframe.

Stop cancels the utterance queue. The prototype also cancels on text/voice changes,
replacement Speak, pagehide and when its tab becomes hidden. It does not observe
new messages in a separate chat tab; automatic cross-tab cancellation is outside
this isolated test. Errors are displayed; Stop is always available if an engine
stalls without emitting an event. Long utterances can be unreliable across
engines; the prototype limits input to 5,000 characters and does not implement
chunking/pause workarounds. No sound, animation, or persisted audio consent occurs
on page load. There are no motion effects, including with reduced motion enabled.

## Manual testing in Codespaces

1. Start Alfred normally with `python -m chainlit run langchain_app.py --host
   0.0.0.0 --port 8000 -w`. Use the forwarded HTTPS origin.
2. Open `/public/tts-spike.html` on that origin in a full Chrome tab. Confirm no
   sound at load. Copy a completed answer from chat and paste it into the box.
3. Check voice loading and the local/remote labels. Click Speak. Listen for voice
   quality, pronunciation and latency; record browser/OS/voice name when reporting.
4. Click Stop mid-speech; Speak again; replace text while speaking; switch voices;
   hide or close the tab. Confirm speech stops and stale callbacks do not change
   the current status. Try empty input, an unavailable voice and a long response.
5. Confirm ordinary chat and dictated submissions still stream with shared memory,
   reset and cancellation. They must never trigger audio on their own.
6. Repeat in the intended browsers. Browser support/available voices and actual
   audio output cannot be established by mocked tests alone.

Run `node --test tests/test_tts.mjs` (Node 18+) for the dependency-free mocked
controller tests, and `python -m unittest discover -s tests -v` for existing
application checks. Node is test tooling only, not a runtime requirement.

## Sources inspected

- [Pinned header/composer implementation](https://github.com/Chainlit/chainlit/blob/1.0.200/frontend/src/components/organisms/chat/inputBox/input.tsx)
- [Pinned speech button](https://github.com/Chainlit/chainlit/blob/1.0.200/frontend/src/components/organisms/chat/inputBox/speechButton.tsx)
- [Pinned configuration extension points](https://github.com/Chainlit/chainlit/blob/1.0.200/backend/chainlit/config.py)
- [SpeechSynthesis API](https://developer.mozilla.org/en-US/docs/Web/API/SpeechSynthesis)
- [Local versus remote voices](https://developer.mozilla.org/en-US/docs/Web/API/SpeechSynthesisVoice/localService)
- [Chrome user activation restriction](https://chromestatus.com/feature/5687444770914304)

Validation performed: 21 existing Python tests and four mocked JS controller
tests passed. Local browser smoke test populated the voice list, remained idle
on load, and manual Speak reached Finished; Stop reported Stopped. Audible
quality and real Codespaces/browser policy behavior still require user testing.
