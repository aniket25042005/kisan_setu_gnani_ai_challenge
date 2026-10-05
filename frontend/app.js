/**
 * KisanSetu — Client-side Audio Engine & UI Controller
 * Powered by Gnani Artha (Prisma v2.5 STT & Timbre v2.5 TTS)
 */

document.addEventListener('DOMContentLoaded', () => {
  // DOM Elements
  const micButton = document.getElementById('micButton');
  const recordingTimer = document.getElementById('recordingTimer');
  const visualizerStatus = document.getElementById('visualizerStatus');
  const canvas = document.getElementById('waveformCanvas');
  const ctx = canvas.getContext('2d');
  const languageSelect = document.getElementById('languageSelect');
  const noisePills = document.querySelectorAll('.noise-pill');
  
  const transcriptDisplay = document.getElementById('transcriptDisplay');
  const voiceResponseDisplay = document.getElementById('voiceResponseDisplay');
  const audioPlayerWrapper = document.getElementById('audioPlayerWrapper');
  const ttsAudioPlayer = document.getElementById('ttsAudioPlayer');
  const replayAudioBtn = document.getElementById('replayAudioBtn');
  const totalLatencyStat = document.getElementById('totalLatencyStat');
  const emptyCardState = document.getElementById('emptyCardState');
  const activeCardContent = document.getElementById('activeCardContent');
  const promptChips = document.querySelectorAll('.prompt-chip');

  // Audio & Recording State
  let isRecording = false;
  let mediaRecorder = null;
  let audioChunks = [];
  let audioContext = null;
  let analyser = null;
  let micStream = null;
  let animFrameId = null;
  let timerInterval = null;
  let recordingSeconds = 0;
  let currentNoiseMode = 'clean';
  let noiseNode = null; // Web Audio noise generator

  // 1. Initialize Ambient Waveform Canvas
  function drawIdleWaveform() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.lineWidth = currentNoiseMode === 'tractor' ? 3 : 2;
    
    // Color & amplitude based on active noise mode
    let strokeColor = 'rgba(52, 211, 153, 0.4)';
    let baseAmp = 6;
    const time = Date.now() * 0.004;

    if (currentNoiseMode === 'tractor') {
      strokeColor = 'rgba(245, 158, 11, 0.85)'; // Vibrant Amber for Tractor
      baseAmp = 18 + Math.sin(time * 6) * 10;   // Pulsating diesel engine rumble waves
    } else if (currentNoiseMode === 'mandi') {
      strokeColor = 'rgba(56, 189, 248, 0.75)'; // Cyan for Mandi chatter
      baseAmp = 12 + (Math.random() * 8);
    } else if (currentNoiseMode === 'telephony') {
      strokeColor = 'rgba(168, 85, 247, 0.75)'; // Purple for Telephony
      baseAmp = 8;
    }

    ctx.strokeStyle = strokeColor;
    ctx.beginPath();

    const sliceWidth = canvas.width / 60;
    let x = 0;

    for (let i = 0; i < 60; i++) {
      let yOffset = Math.sin(i * 0.25 + time) * baseAmp;
      if (currentNoiseMode === 'tractor') {
        // Add mechanical cylinder pulse ripples
        yOffset += Math.sin(i * 0.8 + time * 3) * 4;
      }
      const y = (canvas.height / 2) + yOffset;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
      x += sliceWidth;
    }
    ctx.stroke();

    if (!isRecording) {
      animFrameId = requestAnimationFrame(drawIdleWaveform);
    }
  }
  drawIdleWaveform();

  // 2. Acoustic Noise Selector (The 60s Demo Hook)
  noisePills.forEach(pill => {
    pill.addEventListener('click', async () => {
      noisePills.forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      currentNoiseMode = pill.getAttribute('data-mode');
      
      const labels = {
        clean: '🌿 Clean Studio Audio active',
        tractor: '🚜 Tractor Engine Active: Audio streaming through speakers & mixed into voice!',
        mandi: '🏪 Mandi Crowd Active: Market chatter streaming & mixed into voice!',
        telephony: '📞 8kHz Telephony Filter Active: Simulating 2G narrowband phone call!'
      };
      visualizerStatus.textContent = labels[currentNoiseMode] || 'Ready';
      await playAmbientNoiseEffect(currentNoiseMode);
    });
  });

  // Synthesize background noise soundscapes using Web Audio API
  async function playAmbientNoiseEffect(mode) {
    if (!audioContext) {
      audioContext = new (window.AudioContext || window.webkitAudioContext)();
    }
    if (audioContext.state === 'suspended') {
      try {
        await audioContext.resume();
      } catch (e) {
        console.warn('AudioContext resume error:', e);
      }
    }

    if (noiseNode) {
      try { noiseNode.stop(); noiseNode.disconnect(); } catch (e) {}
      noiseNode = null;
    }

    if (mode === 'clean') return;

    // Create synthetic engine / crowd noise buffer
    const bufferSize = audioContext.sampleRate * 2;
    const noiseBuffer = audioContext.createBuffer(1, bufferSize, audioContext.sampleRate);
    const output = noiseBuffer.getChannelData(0);

    for (let i = 0; i < bufferSize; i++) {
      if (mode === 'tractor') {
        // Deep diesel engine rumble (heavy cylinder chug + exhaust noise)
        const t = i / audioContext.sampleRate;
        const stroke1 = Math.sin(2 * Math.PI * 18 * t); // Low 18Hz idle throb
        const stroke2 = Math.sin(2 * Math.PI * 36 * t) * 0.5; // 2nd harmonic
        const stroke3 = Math.sin(2 * Math.PI * 72 * t) * 0.25; // 3rd harmonic
        const combustionClatter = (Math.random() * 2 - 1) * 0.22 * (stroke1 > 0 ? 1.6 : 0.4);
        output[i] = (stroke1 * 0.5 + stroke2 + stroke3 + combustionClatter) * 0.35;
      } else if (mode === 'mandi') {
        // High frequency crowd chatter + murmurs
        output[i] = (Math.random() * 2 - 1) * 0.22;
      } else {
        // Telephonic hiss
        output[i] = (Math.random() * 2 - 1) * 0.10;
      }
    }

    const whiteNoise = audioContext.createBufferSource();
    whiteNoise.buffer = noiseBuffer;
    whiteNoise.loop = true;

    const gainNode = audioContext.createGain();
    gainNode.gain.value = 0.28; // Clearly audible diesel engine rumble

    whiteNoise.connect(gainNode);
    gainNode.connect(audioContext.destination);
    whiteNoise.start();
    noiseNode = whiteNoise;
  }

  // 3. True 16kHz PCM WAV Recording Logic
  let pcmBuffers = [];
  let recordingLength = 0;
  let scriptProcessor = null;

  micButton.addEventListener('click', async () => {
    if (!isRecording) {
      await startRecording();
    } else {
      stopRecording();
    }
  });

  async function startRecording() {
    try {
      if (!audioContext) {
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
      }
      if (audioContext.state === 'suspended') {
        await audioContext.resume();
      }

      micStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: false, // Keep ambient noise if simulator is active
          autoGainControl: true
        }
      });

      pcmBuffers = [];
      recordingLength = 0;

      const source = audioContext.createMediaStreamSource(micStream);
      analyser = audioContext.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);

      // ScriptProcessor captures raw 32-bit float PCM buffers
      const bufferSize = 4096;
      scriptProcessor = audioContext.createScriptProcessor(bufferSize, 1, 1);

      scriptProcessor.onaudioprocess = e => {
        if (!isRecording) return;
        const channelData = e.inputBuffer.getChannelData(0);
        const bufferCopy = new Float32Array(channelData.length);
        
        for (let i = 0; i < channelData.length; i++) {
          let noiseSample = 0;
          if (currentNoiseMode === 'tractor') {
            const t = (recordingLength + i) / audioContext.sampleRate;
            const stroke1 = Math.sin(2 * Math.PI * 18 * t) * 0.4;
            const stroke2 = Math.sin(2 * Math.PI * 36 * t) * 0.2;
            const clatter = (Math.random() * 2 - 1) * 0.12;
            noiseSample = stroke1 + stroke2 + clatter;
          } else if (currentNoiseMode === 'mandi') {
            noiseSample = (Math.random() * 2 - 1) * 0.14;
          }
          // Mix voice + background noise with clipping guard
          bufferCopy[i] = Math.max(-1, Math.min(1, channelData[i] + noiseSample));
        }

        pcmBuffers.push(bufferCopy);
        recordingLength += channelData.length;
      };

      source.connect(scriptProcessor);
      scriptProcessor.connect(audioContext.destination);

      isRecording = true;
      micButton.classList.add('recording');
      
      const recordingStatusText = {
        clean: '🎙️ Listening to farmer voice... (माइक सुन रहा है)',
        tractor: '🚜 Recording with Live Tractor Noise Injection... (माइक सुन रहा है)',
        mandi: '🏪 Recording with Rural Mandi Chatter Injection... (माइक सुन रहा है)',
        telephony: '📞 Recording with 8kHz Telephony Filter... (माइक सुन रहा है)'
      };
      visualizerStatus.textContent = recordingStatusText[currentNoiseMode] || 'Listening...';

      // Timer
      recordingSeconds = 0;
      recordingTimer.textContent = '00:00';
      timerInterval = setInterval(() => {
        recordingSeconds++;
        const mins = String(Math.floor(recordingSeconds / 60)).padStart(2, '0');
        const secs = String(recordingSeconds % 60).padStart(2, '0');
        recordingTimer.textContent = `${mins}:${secs}`;
      }, 1000);

      // Animate active audio waveform
      drawActiveWaveform();
    } catch (err) {
      console.error('Microphone access error:', err);
      visualizerStatus.textContent = 'Microphone access denied. You can still test using the quick prompt chips below!';
    }
  }

  function stopRecording() {
    if (!isRecording) return;
    isRecording = false;
    micButton.classList.remove('recording');
    clearInterval(timerInterval);
    visualizerStatus.textContent = 'Processing with Gnani Artha stack... (कृपा प्रतीक्षा करें)';

    if (scriptProcessor) {
      scriptProcessor.disconnect();
      scriptProcessor = null;
    }
    if (micStream) {
      micStream.getTracks().forEach(track => track.stop());
    }

    drawIdleWaveform();

    // Flatten buffers
    const mergedBuffer = new Float32Array(recordingLength);
    let offset = 0;
    for (let i = 0; i < pcmBuffers.length; i++) {
      mergedBuffer.set(pcmBuffers[i], offset);
      offset += pcmBuffers[i].length;
    }

    // Downsample to 16,000 Hz for optimal Gnani Prisma recognition
    const targetSampleRate = 16000;
    const downsampled = downsampleBuffer(mergedBuffer, audioContext.sampleRate, targetSampleRate);

    // Encode to true 16-bit linear PCM WAV with valid RIFF header
    const wavBlob = encodeWAV(downsampled, targetSampleRate);
    sendVoiceQuery(wavBlob);
  }

  // Downsample Float32 buffer
  function downsampleBuffer(buffer, sourceRate, targetRate) {
    if (sourceRate === targetRate) return buffer;
    const ratio = sourceRate / targetRate;
    const newLength = Math.round(buffer.length / ratio);
    const result = new Float32Array(newLength);
    let offsetResult = 0;
    let offsetBuffer = 0;
    while (offsetResult < result.length) {
      const nextOffsetBuffer = Math.round((offsetResult + 1) * ratio);
      let accum = 0, count = 0;
      for (let i = offsetBuffer; i < nextOffsetBuffer && i < buffer.length; i++) {
        accum += buffer[i];
        count++;
      }
      result[offsetResult] = count > 0 ? accum / count : 0;
      offsetResult++;
      offsetBuffer = nextOffsetBuffer;
    }
    return result;
  }

  // Encode 16-bit Mono PCM WAV
  function encodeWAV(samples, sampleRate) {
    const buffer = new ArrayBuffer(44 + samples.length * 2);
    const view = new DataView(buffer);

    function writeString(view, offset, string) {
      for (let i = 0; i < string.length; i++) {
        view.setUint8(offset + i, string.charCodeAt(i));
      }
    }

    // RIFF chunk descriptor
    writeString(view, 0, 'RIFF');
    view.setUint32(4, 36 + samples.length * 2, true);
    writeString(view, 8, 'WAVE');

    // "fmt " sub-chunk
    writeString(view, 12, 'fmt ');
    view.setUint32(16, 16, true);          // 16 for PCM
    view.setUint16(20, 1, true);           // Linear quantization
    view.setUint16(22, 1, true);           // Mono (1 channel)
    view.setUint32(24, sampleRate, true);  // 16000
    view.setUint32(28, sampleRate * 2, true); // Byte rate: sampleRate * 1 * 2
    view.setUint16(32, 2, true);           // Block align: 1 * 2
    view.setUint16(34, 16, true);          // Bits per sample: 16

    // "data" sub-chunk
    writeString(view, 36, 'data');
    view.setUint32(40, samples.length * 2, true);

    // Write 16-bit PCM samples
    let offset = 44;
    for (let i = 0; i < samples.length; i++) {
      const s = Math.max(-1, Math.min(1, samples[i]));
      view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
      offset += 2;
    }

    return new Blob([view], { type: 'audio/wav' });
  }

  // Draw active frequency bars on Canvas
  function drawActiveWaveform() {
    if (!isRecording) return;
    requestAnimationFrame(drawActiveWaveform);

    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    analyser.getByteFrequencyData(dataArray);

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const barWidth = (canvas.width / bufferLength) * 2.2;
    let x = 0;

    for (let i = 0; i < bufferLength; i++) {
      const barHeight = (dataArray[i] / 255) * canvas.height * 0.85;
      
      const grad = ctx.createLinearGradient(0, canvas.height, 0, canvas.height - barHeight);
      grad.addColorStop(0, '#10b981');
      grad.addColorStop(1, '#f59e0b');

      ctx.fillStyle = grad;
      ctx.fillRect(x, canvas.height - barHeight, barWidth, barHeight);
      x += barWidth + 2;
    }
  }

  // 4. Send Voice Query to Backend
  async function sendVoiceQuery(audioBlob) {
    const formData = new FormData();
    formData.append('audio_file', audioBlob, 'farmer_voice.wav');
    formData.append('language_code', languageSelect.value);
    formData.append('noise_mode', currentNoiseMode);
    formData.append('voice', 'Nalini');

    try {
      const response = await fetch('/api/voice-query', {
        method: 'POST',
        body: formData
      });

      const data = await response.json();
      if (data.success) {
        renderResults(data);
      } else {
        transcriptDisplay.innerHTML = `<span style="color: #ef4444;">Error: ${data.error || 'Failed to process voice'}</span>`;
        visualizerStatus.textContent = 'Try again or click a quick prompt chip.';
      }
    } catch (err) {
      console.error('API Error:', err);
      transcriptDisplay.innerHTML = `<span style="color: #ef4444;">Server connection error. Check backend status.</span>`;
    }
  }

  // 5. Quick Prompts (Text Fallback)
  promptChips.forEach(chip => {
    chip.addEventListener('click', async () => {
      const promptText = chip.getAttribute('data-prompt');
      const lang = chip.getAttribute('data-lang') || languageSelect.value;
      if (chip.getAttribute('data-lang')) {
        languageSelect.value = lang;
      }

      transcriptDisplay.innerHTML = `<strong>${promptText}</strong>`;
      voiceResponseDisplay.innerHTML = `<span class="placeholder-text">Synthesizing with Gnani Timbre v2.5...</span>`;
      visualizerStatus.textContent = `Processing prompt: "${promptText}"`;

      try {
        const response = await fetch('/api/text-query', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            query: promptText,
            language_code: lang,
            voice: 'Nalini'
          })
        });

        const data = await response.json();
        if (data.success) {
          renderResults(data);
        }
      } catch (err) {
        console.error('Prompt Error:', err);
      }
    });
  });

  // 6. Render Results & Play Audio
  function renderResults(data) {
    // 1. Transcript
    transcriptDisplay.innerHTML = `<strong>${data.transcript || data.query}</strong>`;

    // 2. Voice Response Text
    voiceResponseDisplay.innerHTML = `<span>${data.voice_response}</span>`;

    // 3. Audio Playback (Gnani Timbre or Browser Fallback on Rate Limit)
    if (data.audio_url) {
      ttsAudioPlayer.style.display = 'block';
      ttsAudioPlayer.src = data.audio_url;
      audioPlayerWrapper.style.display = 'flex';
      ttsAudioPlayer.play().catch(e => console.log('Autoplay blocked:', e));

      replayAudioBtn.onclick = () => {
        ttsAudioPlayer.currentTime = 0;
        ttsAudioPlayer.play();
      };
    } else if (data.fallback_tts && 'speechSynthesis' in window) {
      // Graceful fallback to browser speech synthesis if Gnani rate limit is temporarily hit
      ttsAudioPlayer.style.display = 'none';
      audioPlayerWrapper.style.display = 'flex';
      const utterance = new SpeechSynthesisUtterance(data.voice_response);
      utterance.lang = languageSelect.value || 'hi-IN';
      window.speechSynthesis.speak(utterance);

      replayAudioBtn.onclick = () => {
        window.speechSynthesis.cancel();
        window.speechSynthesis.speak(utterance);
      };
    }

    // 4. Latency Metrics
    if (data.metrics) {
      const total = data.metrics.total_roundtrip_ms;
      const stt = data.metrics.stt_latency_ms ? ` • STT: ${data.metrics.stt_latency_ms}ms` : '';
      const tts = data.metrics.tts_latency_ms ? ` • TTS: ${data.metrics.tts_latency_ms}ms` : '';
      totalLatencyStat.textContent = `⚡ Total: ${total}ms${stt}${tts}`;
      visualizerStatus.textContent = `Completed in ${total}ms! Powered by Gnani Artha.`;
    }

    // 5. Render Advisory Card
    renderAdvisoryCard(data.intent, data.title, data.card_data);
  }

  function renderAdvisoryCard(intent, title, cardData) {
    if (!cardData) return;
    emptyCardState.style.display = 'none';
    activeCardContent.style.display = 'block';

    let html = '';

    if (intent === 'mandi') {
      const isOverview = cardData.overview;
      if (isOverview) {
        html = `
          <div class="advisory-badge-pill">APMC Mandi Intelligence</div>
          <h3 class="advisory-title">${title}</h3>
          <p style="color: #cbd5e1; font-size: 1.05rem; margin: 0.5rem 0;">${cardData.overview}</p>
        `;
      } else {
        const trendIcon = cardData.trend === 'up' ? '🔺 Rising' : cardData.trend === 'down' ? '🔻 Falling' : '➡️ Stable';
        html = `
          <div class="advisory-badge-pill">APMC Mandi Intelligence</div>
          <h3 class="advisory-title">${title} — ${cardData.market}</h3>
          <div class="mandi-metric-grid">
            <div class="mandi-metric-box">
              <div class="metric-label">Modal Rate (औसत भाव)</div>
              <div class="metric-val modal">₹${cardData.modal_price}</div>
              <div style="font-size: 0.72rem; color: #94a3b8;">${cardData.unit}</div>
            </div>
            <div class="mandi-metric-box">
              <div class="metric-label">Minimum (न्यूनतम)</div>
              <div class="metric-val">₹${cardData.min_price}</div>
              <div style="font-size: 0.72rem; color: #94a3b8;">${cardData.unit}</div>
            </div>
            <div class="mandi-metric-box">
              <div class="metric-label">Maximum (अधिकतम)</div>
              <div class="metric-val">₹${cardData.max_price}</div>
              <div style="font-size: 0.72rem; color: #94a3b8;">${cardData.unit}</div>
            </div>
          </div>
          <div style="display: flex; justify-content: space-between; font-size: 0.85rem; color: #a7f3d0; margin-top: 0.5rem;">
            <span>Price Trend: <strong>${trendIcon}</strong></span>
            <span>Verified Source: AGMARKNET APMC</span>
          </div>
        `;
      }
    } else if (intent === 'crop_health') {
      html = `
        <div class="advisory-badge-pill" style="border-color: #f59e0b; color: #f59e0b;">Rog Nidan (रोग निदान)</div>
        <h3 class="advisory-title">${title}</h3>
        <p style="font-size: 0.92rem; color: #cbd5e1; margin-bottom: 0.75rem;"><strong>लक्षण (Symptoms):</strong> ${cardData.symptom}</p>
        <div class="remedy-box">
          <div class="remedy-title">🌱 जैविक उपचार (Organic Remedy):</div>
          <div class="remedy-text">${cardData.organic_remedy}</div>
        </div>
        <div class="remedy-box" style="border-left-color: #f59e0b;">
          <div class="remedy-title" style="color: #f59e0b;">💊 रासायनिक छिड़काव (Chemical Remedy):</div>
          <div class="remedy-text">${cardData.chemical_remedy}</div>
        </div>
        <p style="font-size: 0.82rem; color: #94a3b8; margin-top: 0.5rem;">💡 <strong>सावधानी:</strong> ${cardData.prevention}</p>
      `;
    } else if (intent === 'scheme') {
      html = `
        <div class="advisory-badge-pill" style="border-color: #38bdf8; color: #38bdf8;">Sarkari Yojna (सरकारी योजना)</div>
        <h3 class="advisory-title">${title}</h3>
        <div class="scheme-benefit-box">
          <strong style="color: #fbbf24;">लाभ (Benefit):</strong>
          <p style="color: #f8fafc; font-size: 0.92rem; margin-top: 0.25rem;">${cardData.benefit}</p>
        </div>
        <p style="font-size: 0.88rem; color: #cbd5e1; margin-bottom: 0.4rem;"><strong>पात्रता (Eligibility):</strong> ${cardData.eligibility}</p>
        <p style="font-size: 0.88rem; color: #cbd5e1;"><strong>आवेदन कैसे करें:</strong> ${cardData.how_to_avail}</p>
        <div class="helpline-row">
          <span>📞 हेल्पलाइन (Helpline):</span>
          <a href="tel:${cardData.helpline}" style="color: #34d399; text-decoration: underline;">${cardData.helpline}</a>
        </div>
      `;
    } else {
      html = `
        <div class="advisory-badge-pill">KisanSetu Advisory</div>
        <h3 class="advisory-title">${title}</h3>
        <p style="color: #cbd5e1; font-size: 0.95rem; margin-bottom: 0.75rem;">आप नीचे दिए गए किसी भी सवाल पर क्लिक करके सीधा उत्तर सुन सकते हैं:</p>
        <ul style="list-style-type: none; display: flex; flex-direction: column; gap: 0.4rem;">
          ${(cardData.sample_questions || []).map(q => `<li style="color: #34d399; font-size: 0.88rem;">👉 ${q}</li>`).join('')}
        </ul>
      `;
    }

    activeCardContent.innerHTML = html;
  }
});
