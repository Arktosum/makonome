// js/mako_character.js — Custom SVG animated character for Mako
// Minimal clean anime style, blonde hair, green dashboard palette
const MakoCharacter = (() => {

  // ── State ─────────────────────────────────────────────
  let _mood       = 'idle';
  let _speaking   = false;
  let _mouthTimer = null;
  let _blinkTimer = null;
  let _idleTimer  = null;
  let _mounted    = false;

  // mouth shapes as path data — controls the SVG mouth path
  const MOUTHS = {
    idle:      { d: 'M 44 68 Q 50 71 56 68', open: 0 },
    happy:     { d: 'M 42 66 Q 50 74 58 66', open: 0 },
    speaking0: { d: 'M 45 67 Q 50 69 55 67', open: 0.15 },
    speaking1: { d: 'M 44 66 Q 50 73 56 66', open: 0.5  },
    speaking2: { d: 'M 43 65 Q 50 75 57 65', open: 0.85 },
    thinking:  { d: 'M 45 69 Q 50 68 55 69', open: 0 },
    surprised: { d: 'M 46 67 Q 50 75 54 67', open: 0.7 },
    concerned: { d: 'M 45 70 Q 50 66 55 70', open: 0 },
  };

  // eye configs per mood
  const EYES = {
    idle:      { scaleY: 1,    brow: 0  },
    happy:     { scaleY: 0.7,  brow: -3 },
    speaking:  { scaleY: 1,    brow: 0  },
    thinking:  { scaleY: 1,    brow: 4  },
    surprised: { scaleY: 1.3,  brow: -5 },
    concerned: { scaleY: 0.85, brow: 3  },
  };

  // ── SVG template ──────────────────────────────────────
  function _buildSVG() {
    return `
<svg id="mako-svg" viewBox="0 5 100 125" xmlns="http://www.w3.org/2000/svg"
     style="width:100%;height:100%;overflow:hidden">
  <defs>
    <radialGradient id="skinGrad" cx="50%" cy="45%" r="55%">
      <stop offset="0%"   stop-color="#f5e6d3"/>
      <stop offset="100%" stop-color="#e8cdb0"/>
    </radialGradient>
    <radialGradient id="hairGrad" cx="50%" cy="30%" r="70%">
      <stop offset="0%"   stop-color="#f0e080"/>
      <stop offset="100%" stop-color="#c8b840"/>
    </radialGradient>
    <radialGradient id="eyeGrad" cx="40%" cy="35%" r="60%">
      <stop offset="0%"   stop-color="#2affb8"/>
      <stop offset="60%"  stop-color="#0a9a60"/>
      <stop offset="100%" stop-color="#044a30"/>
    </radialGradient>
    <filter id="softGlow">
      <feGaussianBlur stdDeviation="0.8" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <filter id="hairGlow">
      <feGaussianBlur stdDeviation="1.2" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <clipPath id="eyeClipL">
      <ellipse id="eyeClipEllipseL" cx="38" cy="56" rx="6.5" ry="6"/>
    </clipPath>
    <clipPath id="eyeClipR">
      <ellipse id="eyeClipEllipseR" cx="62" cy="56" rx="6.5" ry="6"/>
    </clipPath>
  </defs>

  <!-- ── Neck ── -->
  <rect x="44" y="88" width="12" height="14" rx="4" fill="url(#skinGrad)"/>

  <!-- ── Body / Shoulders ── -->
  <g id="body">
    <!-- shirt -->
    <path d="M 20 130 Q 20 105 35 100 L 50 97 L 65 100 Q 80 105 80 130 Z"
          fill="#0a1f12" stroke="#1df2a0" stroke-width="0.5"/>
    <!-- collar accent -->
    <path d="M 42 100 L 50 107 L 58 100" fill="none" stroke="#1df2a0" stroke-width="0.8" stroke-linecap="round"/>
    <!-- subtle body glow -->
    <path d="M 25 130 Q 25 108 38 103 L 50 100 L 62 103 Q 75 108 75 130"
          fill="none" stroke="#1df2a020" stroke-width="3"/>
  </g>

  <!-- ── Hair back layer ── -->
  <g id="hair-back" filter="url(#hairGlow)">
    <!-- long side strands -->
    <path d="M 22 48 Q 15 65 18 90 Q 20 100 25 105"
          fill="none" stroke="#d4aa30" stroke-width="5" stroke-linecap="round" opacity="0.7"/>
    <path d="M 78 48 Q 85 65 82 90 Q 80 100 75 105"
          fill="none" stroke="#d4aa30" stroke-width="5" stroke-linecap="round" opacity="0.7"/>
    <!-- back hair mass -->
    <path d="M 22 45 Q 18 70 20 95 Q 22 108 30 112 Q 40 116 50 115 Q 60 116 70 112 Q 78 108 80 95 Q 82 70 78 45"
          fill="#c8b840" opacity="0.4"/>
  </g>

  <!-- ── Face ── -->
  <g id="face">
    <!-- face shape -->
    <ellipse cx="50" cy="58" rx="28" ry="32" fill="url(#skinGrad)"/>
    <!-- subtle cheek blush -->
    <ellipse id="blushL" cx="32" cy="65" rx="6" ry="3" fill="#ffb0b0" opacity="0.0"/>
    <ellipse id="blushR" cx="68" cy="65" rx="6" ry="3" fill="#ffb0b0" opacity="0.0"/>
  </g>

  <!-- ── Hair front ── -->
  <g id="hair-front" filter="url(#hairGlow)">
    <!-- main top mass -->
    <path d="M 22 45 Q 24 20 50 18 Q 76 20 78 45 Q 70 35 50 33 Q 30 35 22 45 Z"
          fill="url(#hairGrad)"/>
    <!-- fringe strands -->
    <path d="M 28 38 Q 26 52 30 58 Q 27 50 29 40 Z" fill="#d4c040"/>
    <path d="M 36 30 Q 32 46 34 56 Q 31 45 34 32 Z" fill="#e0cc44"/>
    <path d="M 50 28 Q 48 44 50 54 Q 48 43 49 30 Z" fill="#dcc840"/>
    <path d="M 64 30 Q 68 46 66 56 Q 69 45 66 32 Z" fill="#e0cc44"/>
    <path d="M 72 38 Q 74 52 70 58 Q 73 50 71 40 Z" fill="#d4c040"/>
    <!-- hair highlight -->
    <path d="M 35 22 Q 50 19 65 22" fill="none" stroke="#f8f0a0" stroke-width="1.5"
          stroke-linecap="round" opacity="0.6"/>
    <!-- side part accent -->
    <path d="M 22 45 Q 28 55 26 68 Q 22 60 24 48 Z" fill="#c8b438" opacity="0.8"/>
    <path d="M 78 45 Q 72 55 74 68 Q 78 60 76 48 Z" fill="#c8b438" opacity="0.8"/>
  </g>

  <!-- ── Eyebrows ── -->
  <g id="brows">
    <path id="browL" d="M 31 46 Q 37 43 43 45"
          fill="none" stroke="#8a7020" stroke-width="1.4" stroke-linecap="round"/>
    <path id="browR" d="M 57 45 Q 63 43 69 46"
          fill="none" stroke="#8a7020" stroke-width="1.4" stroke-linecap="round"/>
  </g>

  <!-- ── Eyes ── -->
  <!-- Left eye -->
  <g id="eyeL" style="transform-origin: 38px 56px">
    <ellipse cx="38" cy="56" rx="6.5" ry="6" fill="white"/>
    <g clip-path="url(#eyeClipL)">
      <ellipse cx="38" cy="57" rx="5" ry="5.2" fill="url(#eyeGrad)"/>
      <ellipse cx="38" cy="57" rx="3" ry="3.2" fill="#022a18"/>
      <!-- catchlight -->
      <ellipse cx="39.5" cy="54.5" rx="1.2" ry="1.2" fill="white" opacity="0.9"/>
      <ellipse cx="36.5" cy="58" rx="0.6" ry="0.6" fill="white" opacity="0.4"/>
    </g>
    <!-- eyelid line -->
    <path d="M 31.5 54 Q 38 50 44.5 54" fill="none" stroke="#2a1a08" stroke-width="1"/>
    <!-- lower lash line -->
    <path d="M 32 58 Q 38 61 44 58" fill="none" stroke="#2a1a08" stroke-width="0.5" opacity="0.5"/>
  </g>

  <!-- Right eye -->
  <g id="eyeR" style="transform-origin: 62px 56px">
    <ellipse cx="62" cy="56" rx="6.5" ry="6" fill="white"/>
    <g clip-path="url(#eyeClipR)">
      <ellipse cx="62" cy="57" rx="5" ry="5.2" fill="url(#eyeGrad)"/>
      <ellipse cx="62" cy="57" rx="3" ry="3.2" fill="#022a18"/>
      <!-- catchlight -->
      <ellipse cx="63.5" cy="54.5" rx="1.2" ry="1.2" fill="white" opacity="0.9"/>
      <ellipse cx="60.5" cy="58" rx="0.6" ry="0.6" fill="white" opacity="0.4"/>
    </g>
    <path d="M 55.5 54 Q 62 50 68.5 54" fill="none" stroke="#2a1a08" stroke-width="1"/>
    <path d="M 56 58 Q 62 61 68 58" fill="none" stroke="#2a1a08" stroke-width="0.5" opacity="0.5"/>
  </g>

  <!-- ── Nose ── -->
  <path d="M 48 63 Q 50 66 52 63" fill="none" stroke="#c4a882" stroke-width="0.8"
        stroke-linecap="round" opacity="0.6"/>

  <!-- ── Mouth ── -->
  <g id="mouth-group">
    <!-- mouth bg (inside) — only visible when open -->
    <ellipse id="mouth-inside" cx="50" cy="69" rx="4" ry="0" fill="#1a0808"/>
    <!-- lip shape -->
    <path id="mouth-path" d="M 44 68 Q 50 71 56 68"
          fill="none" stroke="#c06060" stroke-width="1.4" stroke-linecap="round"/>
    <!-- upper lip accent -->
    <path id="upper-lip" d="M 45 68 Q 47 66 50 67 Q 53 66 55 68"
          fill="#d07070" opacity="0.5"/>
  </g>

  <!-- ── Ear accessories ── -->
  <circle cx="22" cy="60" r="2" fill="#1df2a0" opacity="0.7" filter="url(#softGlow)"/>
  <circle cx="78" cy="60" r="2" fill="#1df2a0" opacity="0.7" filter="url(#softGlow)"/>

  <!-- ── Status indicator ── (green ring that pulses when speaking) -->
  <circle id="status-ring" cx="50" cy="58" r="33"
          fill="none" stroke="#1df2a0" stroke-width="0.3" opacity="0.15"/>

  <!-- ── Ambient particles ── -->
  <g id="particles" opacity="0.4">
    <circle class="particle" cx="15" cy="40" r="0.8" fill="#1df2a0"/>
    <circle class="particle" cx="85" cy="30" r="0.6" fill="#1df2a0"/>
    <circle class="particle" cx="10" cy="80" r="0.5" fill="#1df2a0"/>
    <circle class="particle" cx="90" cy="70" r="0.7" fill="#1df2a0"/>
    <circle class="particle" cx="20" cy="110" r="0.4" fill="#1df2a0"/>
    <circle class="particle" cx="82" cy="105" r="0.5" fill="#1df2a0"/>
  </g>
</svg>`;
  }

  // ── CSS animations ────────────────────────────────────
  function _buildCSS() {
    return `
<style id="mako-char-styles">
  #mako-char-wrap {
    width: 100%;
    height: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    position: relative;
    overflow: hidden;
  }

  #mako-svg {
    filter: drop-shadow(0 0 12px #1df2a020);
    transition: filter 0.4s ease;
  }

  #mako-svg.speaking {
    filter: drop-shadow(0 0 20px #1df2a040);
  }

  /* idle breathing — subtle vertical bob */
  @keyframes mako-breathe {
    0%, 100% { transform: translateY(0px);   }
    50%       { transform: translateY(-3px);  }
  }

  /* hair sway */
  @keyframes mako-hair-sway {
    0%, 100% { transform: rotate(0deg);   }
    25%       { transform: rotate(0.8deg);  }
    75%       { transform: rotate(-0.8deg); }
  }

  /* particle float */
  @keyframes mako-particle-float {
    0%, 100% { transform: translateY(0)   opacity(0.4); }
    50%       { transform: translateY(-8px) opacity(0.8); }
  }

  /* speaking pulse on status ring */
  @keyframes mako-ring-pulse {
    0%, 100% { opacity: 0.1; r: 33; }
    50%       { opacity: 0.4; r: 35; }
  }

  /* thinking bob */
  @keyframes mako-think {
    0%, 100% { transform: translateY(0) rotate(0deg);   }
    30%       { transform: translateY(-2px) rotate(-1deg); }
    70%       { transform: translateY(-1px) rotate(1deg);  }
  }

  /* entrance animation */
  @keyframes mako-enter {
    from { opacity: 0; transform: translateY(20px) scale(0.95); }
    to   { opacity: 1; transform: translateY(0)    scale(1);    }
  }

  #mako-svg { animation: mako-enter 0.8s ease forwards; }

  #mako-svg #body { 
    animation: mako-breathe 3.5s ease-in-out infinite;
    transform-origin: 50px 100px;
  }

  #mako-svg #face { 
    animation: mako-breathe 3.5s ease-in-out infinite;
    transform-origin: 50px 60px;
  }

  #mako-svg #hair-front {
    animation: mako-breathe 3.5s ease-in-out infinite,
               mako-hair-sway 6s ease-in-out infinite;
    transform-origin: 50px 30px;
  }

  #mako-svg #hair-back {
    animation: mako-breathe 3.5s ease-in-out infinite,
               mako-hair-sway 6s ease-in-out infinite 0.3s;
    transform-origin: 50px 30px;
  }

  #mako-svg #brows {
    animation: mako-breathe 3.5s ease-in-out infinite;
    transform-origin: 50px 60px;
  }

  #mako-svg #eyeL,
  #mako-svg #eyeR,
  #mako-svg #mouth-group,
  #mako-svg #blushL,
  #mako-svg #blushR {
    animation: mako-breathe 3.5s ease-in-out infinite;
    transform-origin: 50px 60px;
  }

  #mako-svg .particle:nth-child(1) { animation: mako-particle-float 4s ease-in-out infinite 0s; }
  #mako-svg .particle:nth-child(2) { animation: mako-particle-float 4s ease-in-out infinite 0.7s; }
  #mako-svg .particle:nth-child(3) { animation: mako-particle-float 4s ease-in-out infinite 1.4s; }
  #mako-svg .particle:nth-child(4) { animation: mako-particle-float 4s ease-in-out infinite 2.1s; }
  #mako-svg .particle:nth-child(5) { animation: mako-particle-float 4s ease-in-out infinite 2.8s; }
  #mako-svg .particle:nth-child(6) { animation: mako-particle-float 4s ease-in-out infinite 3.5s; }

  /* mood classes applied to svg */
  #mako-svg.thinking #face,
  #mako-svg.thinking #brows,
  #mako-svg.thinking #eyeL,
  #mako-svg.thinking #eyeR,
  #mako-svg.thinking #mouth-group {
    animation: mako-breathe 3.5s ease-in-out infinite,
               mako-think 2s ease-in-out infinite !important;
    transform-origin: 50px 60px;
  }
</style>`;
  }

  // ── Mount character into DOM ──────────────────────────
  function mount(containerId) {
    const container = document.getElementById(containerId);
    if (!container) { console.error('Character container not found:', containerId); return; }

    container.innerHTML = `
      <div id="mako-char-wrap">
        ${_buildCSS()}
        ${_buildSVG()}
      </div>`;

    _mounted = true;
    _startBlink();
    _startIdleGaze();
    console.log('✅ Mako character mounted!');
  }

  // ── Blink system ──────────────────────────────────────
  function _startBlink() {
    function scheduleBlink() {
      const delay = 2000 + Math.random() * 4000;
      _blinkTimer = setTimeout(() => {
        _blink();
        scheduleBlink();
      }, delay);
    }
    scheduleBlink();
  }

  function _blink() {
    const eyeL = document.getElementById('eyeL');
    const eyeR = document.getElementById('eyeR');
    if (!eyeL || !eyeR) return;

    // squeeze eyes shut
    eyeL.style.transition = 'transform 0.06s ease';
    eyeR.style.transition = 'transform 0.06s ease';
    eyeL.style.transform  = 'scaleY(0.05)';
    eyeR.style.transform  = 'scaleY(0.05)';

    setTimeout(() => {
      eyeL.style.transition = 'transform 0.1s ease';
      eyeR.style.transition = 'transform 0.1s ease';
      eyeL.style.transform  = '';
      eyeR.style.transform  = '';
    }, 100);
  }

  // ── Idle gaze drift ───────────────────────────────────
  function _startIdleGaze() {
    function scheduleGaze() {
      const delay = 3000 + Math.random() * 5000;
      _idleTimer = setTimeout(() => {
        if (!_speaking) _driftGaze();
        scheduleGaze();
      }, delay);
    }
    scheduleGaze();
  }

  function _driftGaze() {
    // slight pupil movement — look around naturally
    const eyeClipL = document.getElementById('eyeClipEllipseL');
    const eyeClipR = document.getElementById('eyeClipEllipseR');
    if (!eyeClipL) return;

    const dx = (Math.random() - 0.5) * 2;
    const dy = (Math.random() - 0.5) * 1;

    // we move the clip path to reveal different parts of the iris
    eyeClipL.setAttribute('cx', 38 + dx);
    eyeClipL.setAttribute('cy', 56 + dy);
    eyeClipR.setAttribute('cx', 62 + dx);
    eyeClipR.setAttribute('cy', 56 + dy);

    // return to center after a moment
    setTimeout(() => {
      eyeClipL.setAttribute('cx', '38');
      eyeClipL.setAttribute('cy', '56');
      eyeClipR.setAttribute('cx', '62');
      eyeClipR.setAttribute('cy', '56');
    }, 1500);
  }

  // ── Mouth animation ───────────────────────────────────
  function startSpeaking() {
    if (!_mounted) return;
    _speaking = true;

    const svg = document.getElementById('mako-svg');
    if (svg) svg.classList.add('speaking');

    // pulse the status ring
    const ring = document.getElementById('status-ring');
    if (ring) ring.style.animation = 'mako-ring-pulse 0.5s ease-in-out infinite';

    const shapes = ['speaking0', 'speaking1', 'speaking2', 'speaking1', 'speaking0'];
    let i = 0;

    _mouthTimer = setInterval(() => {
      if (!_speaking) {
        clearInterval(_mouthTimer);
        _setMouth('idle');
        return;
      }
      // cycle through mouth shapes with slight randomness
      const shape = shapes[i % shapes.length];
      const jitter = Math.random() > 0.3 ? shape : 'speaking0';
      _setMouth(jitter);
      i++;
    }, 100 + Math.random() * 60);
  }

  function stopSpeaking() {
    if (!_mounted) return;
    _speaking = false;
    clearInterval(_mouthTimer);

    const svg = document.getElementById('mako-svg');
    if (svg) svg.classList.remove('speaking');

    const ring = document.getElementById('status-ring');
    if (ring) ring.style.animation = '';

    // smooth close
    setTimeout(() => _setMouth(_mood === 'happy' ? 'happy' : 'idle'), 80);
  }

  function _setMouth(shapeName) {
    const mouth  = document.getElementById('mouth-path');
    const inside = document.getElementById('mouth-inside');
    const upper  = document.getElementById('upper-lip');
    if (!mouth) return;

    const shape = MOUTHS[shapeName] || MOUTHS.idle;
    mouth.setAttribute('d', shape.d);

    // show mouth interior when open
    if (inside) inside.setAttribute('ry', (shape.open * 3).toFixed(2));

    // shift upper lip up slightly when open
    if (upper) upper.setAttribute('opacity', shape.open > 0.3 ? '0.8' : '0.5');
  }

  // ── Expression / mood ─────────────────────────────────
  function setMood(mood) {
    if (!_mounted) return;
    _mood = mood;

    const svg   = document.getElementById('mako-svg');
    const browL = document.getElementById('browL');
    const browR = document.getElementById('browR');
    const blushL = document.getElementById('blushL');
    const blushR = document.getElementById('blushR');
    const eyeL  = document.getElementById('eyeL');
    const eyeR  = document.getElementById('eyeR');

    if (!svg) return;

    // remove all mood classes
    svg.classList.remove('happy','thinking','surprised','concerned','idle');
    svg.classList.add(mood);

    const eyeCfg = EYES[mood] || EYES.idle;

    switch(mood) {
      case 'happy':
        // raised brows, squinted happy eyes, blush, smile
        if (browL) browL.setAttribute('d', 'M 31 44 Q 37 41 43 43');
        if (browR) browR.setAttribute('d', 'M 57 43 Q 63 41 69 44');
        if (eyeL)  { eyeL.style.transform = 'scaleY(0.75)'; eyeL.style.transition = 'transform 0.3s ease'; }
        if (eyeR)  { eyeR.style.transform = 'scaleY(0.75)'; eyeR.style.transition = 'transform 0.3s ease'; }
        if (blushL) blushL.setAttribute('opacity', '0.35');
        if (blushR) blushR.setAttribute('opacity', '0.35');
        if (!_speaking) _setMouth('happy');
        break;

      case 'thinking':
        // furrowed brows, normal eyes, slight frown
        if (browL) browL.setAttribute('d', 'M 31 47 Q 37 45 43 47');
        if (browR) browR.setAttribute('d', 'M 57 47 Q 63 45 69 47');
        if (eyeL)  { eyeL.style.transform = ''; }
        if (eyeR)  { eyeR.style.transform = ''; }
        if (blushL) blushL.setAttribute('opacity', '0');
        if (blushR) blushR.setAttribute('opacity', '0');
        if (!_speaking) _setMouth('thinking');
        break;

      case 'surprised':
        // raised brows, wide eyes, open mouth
        if (browL) browL.setAttribute('d', 'M 31 43 Q 37 40 43 42');
        if (browR) browR.setAttribute('d', 'M 57 42 Q 63 40 69 43');
        if (eyeL)  { eyeL.style.transform = 'scaleY(1.2)'; eyeL.style.transition = 'transform 0.15s ease'; }
        if (eyeR)  { eyeR.style.transform = 'scaleY(1.2)'; eyeR.style.transition = 'transform 0.15s ease'; }
        if (blushL) blushL.setAttribute('opacity', '0.2');
        if (blushR) blushR.setAttribute('opacity', '0.2');
        if (!_speaking) _setMouth('surprised');
        // return to normal after a beat
        setTimeout(() => { if (_mood === 'surprised') setMood('idle'); }, 2000);
        break;

      case 'concerned':
        if (browL) browL.setAttribute('d', 'M 31 45 Q 37 48 43 46');
        if (browR) browR.setAttribute('d', 'M 57 46 Q 63 48 69 45');
        if (eyeL)  { eyeL.style.transform = 'scaleY(0.9)'; }
        if (eyeR)  { eyeR.style.transform = 'scaleY(0.9)'; }
        if (blushL) blushL.setAttribute('opacity', '0');
        if (blushR) blushR.setAttribute('opacity', '0');
        if (!_speaking) _setMouth('concerned');
        break;

      case 'idle':
      default:
        if (browL) browL.setAttribute('d', 'M 31 46 Q 37 43 43 45');
        if (browR) browR.setAttribute('d', 'M 57 45 Q 63 43 69 46');
        if (eyeL)  { eyeL.style.transform = ''; eyeL.style.transition = 'transform 0.4s ease'; }
        if (eyeR)  { eyeR.style.transform = ''; eyeR.style.transition = 'transform 0.4s ease'; }
        if (blushL) blushL.setAttribute('opacity', '0');
        if (blushR) blushR.setAttribute('opacity', '0');
        if (!_speaking) _setMouth('idle');
        break;
    }
  }

  // ── Detect mood from message text ─────────────────────
  function detectMood(text) {
    const t = text.toLowerCase();
    if (/\b(great|awesome|love|happy|excited|yay|nice|wonderful|amazing)\b/.test(t)) return 'happy';
    if (/\b(hmm|think|wonder|maybe|consider|perhaps|let me|searching)\b/.test(t))    return 'thinking';
    if (/\b(oh|wow|really|seriously|no way|what)\b/.test(t))                         return 'surprised';
    if (/\b(sorry|worried|concern|sad|difficult|hard|tough)\b/.test(t))              return 'concerned';
    return 'happy'; // default to happy when speaking
  }

  return {
    mount,
    startSpeaking,
    stopSpeaking,
    setMood,
    detectMood,
  };
})();