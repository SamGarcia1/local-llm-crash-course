// Isolated browser experiment: no access to Chainlit messages or session state.
export function createSpeaker(synth, Utterance, report) {
  let generation = 0;
  let current = null;
  function stop(status = 'Stopped') {
    generation += 1;
    current = null;
    synth.cancel();
    report(status);
  }
  function speak(text, voice) {
    stop('Idle');
    if (!text.trim()) { report('Enter a response to speak.'); return; }
    const id = generation;
    current = new Utterance(text.trim());
    if (voice) { current.voice = voice; current.lang = voice.lang; }
    current.onstart = () => { if (id === generation) report('Speaking'); };
    current.onend = () => {
      if (id === generation) { current = null; report('Finished'); }
    };
    current.onerror = (event) => {
      if (id === generation) {
        current = null;
        report(`Speech failed (${event.error || 'unknown error'}). Try Speak again or another voice.`);
      }
    };
    report('Starting speech…');
    try { synth.resume(); synth.speak(current); }
    catch { stop('Speech unavailable. Try another voice or browser.'); }
  }
  return { speak, stop };
}

if (typeof document !== 'undefined') {
  const text = document.querySelector('#text');
  const voices = document.querySelector('#voices');
  const speak = document.querySelector('#speak');
  const stop = document.querySelector('#stop');
  const status = document.querySelector('#status');
  const synth = window.speechSynthesis;
  if (!synth || !window.SpeechSynthesisUtterance) {
    status.textContent = 'Speech synthesis is unavailable in this browser.';
    speak.disabled = stop.disabled = true;
  } else {
    const player = createSpeaker(synth, window.SpeechSynthesisUtterance,
      (value) => { status.textContent = value; });
    let available = [];
    function refreshVoices() {
      const selected = voices.value;
      available = synth.getVoices();
      voices.replaceChildren(new Option('Browser default (service may be remote)', ''));
      for (const voice of available) {
        voices.add(new Option(`${voice.name} — ${voice.lang} (${voice.localService ? 'local' : 'remote'})`, voice.voiceURI));
      }
      if (available.some(v => v.voiceURI === selected)) voices.value = selected;
    }
    refreshVoices();
    synth.addEventListener('voiceschanged', refreshVoices);
    speak.addEventListener('click', () => player.speak(text.value,
      available.find(v => v.voiceURI === voices.value)));
    stop.addEventListener('click', () => player.stop());
    text.addEventListener('input', () => player.stop('Idle — text changed'));
    voices.addEventListener('change', () => player.stop('Idle — voice changed'));
    window.addEventListener('pagehide', () => player.stop());
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) player.stop();
    });
  }
}
