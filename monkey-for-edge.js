// ==UserScript==
// @name         Edge 专属：发音 + 翻译气泡 + 高级控制舱 (防抖终极版)
// @namespace    http://tampermonkey.net/
// @version      12.0
// @description  加入 CSS 绝对隔离，修复按钮 Hover 抖动问题；保留语音记忆与断点手动续读
// @author       极客助手
// @match        *://*/*
// @match        file:///*
// @grant        none
// ==/UserScript==

(function() {
    'use strict';

    // === 确保语音库就绪 ===
    window.speechSynthesis.getVoices();

    // === 第一步：样式注入 (加入极度严格的 CSS 隔离防抖) ===
    let style = document.createElement('style');
    style.innerHTML = `
        strong, em { position: relative !important; cursor: pointer !important; display: inline-block !important; }
        .translation-bubble {
            position: absolute !important; bottom: 125% !important; left: 50% !important;
            transform: translateX(-50%) scale(0.8) !important; background-color: #e74c3c !important; 
            color: #ffffff !important; padding: 6px 12px !important; border-radius: 6px !important; 
            font-size: 14px !important; font-weight: normal !important; font-style: normal !important; 
            white-space: nowrap !important; box-shadow: 0 4px 15px rgba(0,0,0,0.2) !important; 
            opacity: 0 !important; pointer-events: none !important; 
            transition: opacity 0.2s ease, transform 0.2s ease !important; z-index: 99999 !important;            
        }
        .translation-bubble::after {
            content: "" !important; position: absolute !important; top: 100% !important; left: 50% !important;
            transform: translateX(-50%) !important; border-width: 6px !important; border-style: solid !important;
            border-color: #e74c3c transparent transparent transparent !important;
        }
        strong:hover .translation-bubble, em:hover .translation-bubble, 
        .translation-bubble.force-show { 
            opacity: 1 !important; transform: translateX(-50%) scale(1) !important; 
            background-color: #e74c3c !important; 
        }
        .translation-bubble.force-show::after { border-color: #e74c3c transparent transparent transparent !important; }

        #geek-tts-panel {
            position: fixed !important; bottom: 30px !important; right: 30px !important; background-color: rgba(30, 41, 59, 0.95) !important;
            padding: 16px !important; border-radius: 12px !important; box-shadow: 0 10px 30px rgba(0,0,0,0.3) !important; backdrop-filter: blur(10px) !important;
            z-index: 100000 !important; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
            color: white !important; display: flex !important; flex-direction: column !important; gap: 12px !important; user-select: none !important; 
            border: 1px solid rgba(255,255,255,0.1) !important; box-sizing: border-box !important; margin: 0 !important;
        }
        .geek-row { display: flex !important; gap: 8px !important; align-items: center !important; justify-content: space-between !important; }
        
        .geek-select { 
            background-color: rgba(0,0,0,0.4) !important; border: 1px solid rgba(255,255,255,0.2) !important; 
            color: white !important; padding: 6px 8px !important; border-radius: 6px !important; outline: none !important; 
            width: 100% !important; max-width: 200px !important; font-size: 13px !important; cursor: pointer !important; 
            box-sizing: border-box !important; margin: 0 !important; height: auto !important;
        }
        
        /* 核心防抖修复：锁死按钮边界，只允许背景色参与动画 */
        .geek-btn { 
            background-color: rgba(255,255,255,0.1) !important; 
            border: 1px solid transparent !important; /* 提前占位，防止外部 hover 注入边框 */
            color: white !important; padding: 8px 14px !important; border-radius: 6px !important; 
            cursor: pointer !important; font-size: 14px !important; 
            transition: background-color 0.2s ease !important; /* 严禁使用 all */
            display: flex !important; align-items: center !important; gap: 6px !important; 
            flex: 1 !important; justify-content: center !important; 
            box-sizing: border-box !important; margin: 0 !important; line-height: 1.2 !important; height: auto !important;
        }
        .geek-btn:hover { background-color: rgba(255,255,255,0.2) !important; }
        .geek-btn.active { background-color: rgba(52, 152, 219, 0.8) !important; }
        .geek-btn.danger { background-color: rgba(231, 76, 60, 0.8) !important; }
        .geek-btn.danger:hover { background-color: rgba(192, 57, 43, 1) !important; }
    `;
    document.head.appendChild(style);

    // === 第二步：气泡 DOM 重构 ===
    function buildBubbles() {
        document.querySelectorAll('strong, em').forEach(wordNode => {
            if (wordNode.querySelector('.translation-bubble')) return;
            let nextNode = wordNode.nextSibling;
            if (nextNode && nextNode.nodeType === Node.TEXT_NODE) {
                let text = nextNode.nodeValue;
                let match = text.match(/^\s*(\(.*?\))/);
                if (match) {
                    let translationText = match[1];
                    nextNode.nodeValue = text.substring(match[0].length);
                    let bubble = document.createElement('span');
                    bubble.className = 'translation-bubble';
                    bubble.textContent = translationText;
                    wordNode.appendChild(bubble);
                }
            }
        });
    }
    setTimeout(buildBubbles, 500); 
    setTimeout(buildBubbles, 1500);

    // === 第三步：构建悬浮控制舱 UI ===
    let oldPanel = document.getElementById('geek-tts-panel');
    if (oldPanel) oldPanel.remove();

    let panel = document.createElement('div');
    panel.id = 'geek-tts-panel';
    panel.innerHTML = `
        <div class="geek-row">
            <span style="font-size: 13px; opacity: 0.8;">🗣 朗读人:</span>
            <select id="geek-voice-select" class="geek-select"><option>加载语音中...</option></select>
        </div>
        <div class="geek-row">
            <button id="geek-btn-play" class="geek-btn">▶️ 全文朗读</button>
            <button id="geek-btn-stop" class="geek-btn danger">⏹ 停止</button>
        </div>
    `;
    document.body.appendChild(panel);

    let voiceSelect = document.getElementById('geek-voice-select');
    let btnPlay = document.getElementById('geek-btn-play');
    let btnStop = document.getElementById('geek-btn-stop');

    // === 第四步：加载语音库 (带用户选择记忆) ===
    let globalVoices = [];
    let userSelectedVoiceName = null; 

    voiceSelect.addEventListener('change', () => {
        if (globalVoices.length > 0) {
            userSelectedVoiceName = globalVoices[voiceSelect.value].name;
        }
    });

    function loadVoices() {
        let voices = window.speechSynthesis.getVoices();
        if (voices.length === 0) return;
        globalVoices = voices.filter(v => v.lang.includes('zh') || v.lang.includes('en'))
                             .sort((a, b) => (b.name.includes('Natural') ? 1 : 0) - (a.name.includes('Natural') ? 1 : 0));
        voiceSelect.innerHTML = '';
        
        globalVoices.forEach((voice, index) => {
            let option = document.createElement('option');
            option.value = index;
            let displayName = voice.name.replace('Microsoft', '').replace('Online (Natural)', '🌟自然').trim();
            option.textContent = `${displayName} (${voice.lang})`;
            
            if (userSelectedVoiceName) {
                if (voice.name === userSelectedVoiceName) option.selected = true;
            } else {
                if (voice.name.includes('Xiaoxiao Online (Natural)')) option.selected = true;
            }
            
            voiceSelect.appendChild(option);
        });
    }
    window.speechSynthesis.onvoiceschanged = loadVoices;
    loadVoices();

    // === 第五步：音画同步核心追踪引擎 ===
    let markers = [];
    let fullCleanText = "";
    let globalTextOffset = 0;
    let currentActiveBubble = null;

    function clearActiveBubble() {
        if (currentActiveBubble) {
            currentActiveBubble.classList.remove('force-show');
            currentActiveBubble = null;
        }
    }

    function preparePlaybackData() {
        let cloneBody = document.body.cloneNode(true);
        cloneBody.querySelectorAll('.translation-bubble').forEach(b => b.remove());
        let p = cloneBody.querySelector('#geek-tts-panel');
        if (p) p.remove();

        let originalTargets = document.querySelectorAll('strong, em');
        let clonedTargets = cloneBody.querySelectorAll('strong, em');
        
        clonedTargets.forEach((el, index) => {
            el.insertAdjacentText('afterbegin', `\u200B__TTS_${index}__\u200B`);
        });

        let rawText = cloneBody.innerText;
        let cleanText = "";
        let regex = /\u200B__TTS_(\d+)__\u200B/g;
        let match;
        let lastIndex = 0;
        
        markers = [];
        while ((match = regex.exec(rawText)) !== null) {
            cleanText += rawText.substring(lastIndex, match.index);
            let targetIndex = parseInt(match[1]);
            let originalEl = originalTargets[targetIndex];
            
            if (originalEl && originalEl.querySelector('.translation-bubble')) {
                let wordLength = originalEl.childNodes[0].textContent.trim().length;
                markers.push({
                    bubble: originalEl.querySelector('.translation-bubble'),
                    start: cleanText.length,
                    end: cleanText.length + wordLength
                });
            }
            lastIndex = regex.lastIndex;
        }
        cleanText += rawText.substring(lastIndex);
        fullCleanText = cleanText;
        globalTextOffset = 0;
    }

    // === 第六步：手动待机状态机 ===
    let currentState = 'idle'; 
    let currentUtterance = null;
    let remainingText = "";    
    let lastCharIndex = 0;     

    function resetPlayerState() {
        currentState = 'idle';
        btnPlay.innerHTML = '▶️ 全文朗读';
        btnPlay.classList.remove('active');
        remainingText = "";
        lastCharIndex = 0;
        clearActiveBubble();
    }

    function startPlayback(textToPlay) {
        if (!textToPlay || !textToPlay.trim()) {
            resetPlayerState();
            return;
        }
        
        remainingText = textToPlay;
        lastCharIndex = 0;
        
        currentUtterance = new SpeechSynthesisUtterance(remainingText);
        if (globalVoices.length > 0) currentUtterance.voice = globalVoices[voiceSelect.value];
        currentUtterance.rate = 1.0;

        currentUtterance.onboundary = (e) => { 
            lastCharIndex = e.charIndex; 
            let absIndex = globalTextOffset + e.charIndex;
            
            let activeMarker = markers.find(m => absIndex >= m.start - 2 && absIndex <= m.end + 2);
            if (activeMarker) {
                if (currentActiveBubble !== activeMarker.bubble) {
                    clearActiveBubble();
                    currentActiveBubble = activeMarker.bubble;
                    currentActiveBubble.classList.add('force-show');
                }
            } else {
                clearActiveBubble();
            }
        };

        currentUtterance.onstart = () => {
            currentState = 'playing';
            btnPlay.innerHTML = '⏸ 暂停';
            btnPlay.classList.add('active');
        };

        currentUtterance.onend = () => {
            if (currentState === 'playing') resetPlayerState();
        };

        window.speechSynthesis.speak(currentUtterance);
    }

    btnPlay.addEventListener('click', () => {
        if (currentState === 'idle') {
            preparePlaybackData(); 
            startPlayback(fullCleanText);
        } else if (currentState === 'playing') {
            window.speechSynthesis.pause();
            currentState = 'paused';
            btnPlay.innerHTML = '▶️ 继续';
            btnPlay.classList.remove('active');
        } else if (currentState === 'paused') {
            window.speechSynthesis.resume();
            currentState = 'playing';
            btnPlay.innerHTML = '⏸ 暂停';
            btnPlay.classList.add('active');
        } else if (currentState === 'manual_standby') {
            startPlayback(remainingText);
        }
    });

    btnStop.addEventListener('click', () => {
        currentState = 'idle'; 
        window.speechSynthesis.cancel();
        resetPlayerState();
    });

    // === 第七步：单词点击阻断 ===
    document.addEventListener('click', function(e) {
        if (e.target.closest('#geek-tts-panel')) return;
        if (['INPUT', 'TEXTAREA', 'BUTTON', 'A', 'SELECT', 'OPTION'].includes(e.target.tagName)) return;

        let range;
        if (document.caretRangeFromPoint) range = document.caretRangeFromPoint(e.clientX, e.clientY);

        if (range && range.startContainer.nodeType === Node.TEXT_NODE) {
            let node = range.startContainer;
            let offset = range.startOffset;
            let text = node.textContent;

            let start = offset;
            while (start > 0 && /\w/.test(text[start - 1])) { start--; }
            let end = offset;
            while (end < text.length && /\w/.test(text[end])) { end++; }

            let word = text.slice(start, end).trim();

            if (word && /^[a-zA-Z]+$/.test(word)) {
                let selectRange = document.createRange();
                selectRange.setStart(node, start);
                selectRange.setEnd(node, end);
                let sel = window.getSelection();
                sel.removeAllRanges();
                sel.addRange(selectRange);

                if (currentState === 'playing' || currentState === 'paused') {
                    globalTextOffset += lastCharIndex;
                    remainingText = remainingText.substring(lastCharIndex);
                }
                
                currentState = 'manual_standby';
                window.speechSynthesis.cancel(); 
                clearActiveBubble(); 
                
                btnPlay.innerHTML = '▶️ 继续';
                btnPlay.classList.remove('active');

                let utterance = new SpeechSynthesisUtterance(word);
                let enVoice = globalVoices.find(v => v.name.includes('Aria Online (Natural)')) || 
                              globalVoices.find(v => v.name.includes('Jenny Online (Natural)'));
                if (enVoice) utterance.voice = enVoice;
                utterance.rate = 0.9;

                window.speechSynthesis.speak(utterance);
            }
        }
    });

})();