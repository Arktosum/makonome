// js/voice.js — browser microphone using Web Speech API
const Voice = (() => {
  let _recognition = null;
  let _isRecording = false;

  function isSupported() {
    return 'webkitSpeechRecognition' in window || 'SpeechRecognition' in window;
  }

  function init(onResult) {
    if (!isSupported()) {
      console.warn('Web Speech API not supported in this browser');
      document.getElementById('mic-btn').style.display = 'none';
      return;
    }

    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    _recognition = new SR();
    _recognition.continuous = false;
    _recognition.interimResults = false;
    _recognition.lang = 'en-US';

    _recognition.onresult = (e) => {
      const transcript = e.results[0][0].transcript;
      onResult(transcript);
    };

    _recognition.onend = () => {
      _isRecording = false;
      document.getElementById('mic-btn').classList.remove('recording');
      document.getElementById('mic-btn').textContent = '🎤';
    };

    _recognition.onerror = (e) => {
      console.error('Speech recognition error:', e.error);
      _isRecording = false;
      document.getElementById('mic-btn').classList.remove('recording');
      document.getElementById('mic-btn').textContent = '🎤';
    };
  }

  function toggle() {
    if (!_recognition) return;
    if (_isRecording) {
      _recognition.stop();
    } else {
      _isRecording = true;
      document.getElementById('mic-btn').classList.add('recording');
      document.getElementById('mic-btn').textContent = '⏹';
      _recognition.start();
    }
  }

  return { init, toggle, isSupported };
})();