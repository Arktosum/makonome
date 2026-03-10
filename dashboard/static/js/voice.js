// js/voice.js — browser speech recognition
const Voice = (() => {
  let _recognition = null;
  let _active = false;
  let _onResult = null;

  function init(onResult) {
    _onResult = onResult;
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) { console.warn('[Voice] Speech recognition not supported'); return; }
    _recognition = new SR();
    _recognition.lang = 'en-US';
    _recognition.interimResults = false;
    _recognition.maxAlternatives = 1;

    _recognition.onresult = (e) => {
      const transcript = e.results[0][0].transcript;
      _setRecording(false);
      if (_onResult) _onResult(transcript);
    };

    _recognition.onerror = () => _setRecording(false);
    _recognition.onend   = () => _setRecording(false);
  }

  function toggle() {
    if (!_recognition) return;
    if (_active) {
      _recognition.stop();
      _setRecording(false);
    } else {
      _recognition.start();
      _setRecording(true);
    }
  }

  function _setRecording(state) {
    _active = state;
    document.getElementById('mic-btn')?.classList.toggle('recording', state);
  }

  return { init, toggle };
})();