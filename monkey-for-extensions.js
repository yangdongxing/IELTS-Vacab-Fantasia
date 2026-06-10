// ==UserScript==
// @name         Edge 专属：发音 + 翻译气泡 + 高级控制舱 (Mac 兼容 + R键重读防冲突)
// @namespace    http://tampermonkey.net/
// @version      24.0
// @description  修复 R 键重读功能劫持 Command+R 导致无法刷新页面的 Bug。
// @author       极客助手
// @match        file:///Users/ydx/Documents/IELTS/tools/IELTS-Vacab-Fantasia/*
// @grant        none
// ==/UserScript==

(function() {
    'use strict';

    // === 确保语音库就绪 ===
    window.speechSynthesis.getVoices();

    // === 第一步：样式注入 ===
    let style = document.createElement('style');
    style.innerHTML = `
        strong, em { position: relative !important; cursor: grab !important; display: inline-block !important; }
        strong:active, em:active { cursor: grabbing !important; }

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
            opacity: 1 !important; transform: translateX(-50%) scale(1) !important; background-color: #e74c3c !important;
        }
        .translation-bubble.force-show::after { border-color: #e74c3c transparent transparent transparent !important; }

        #geek-tts-panel {
            position: fixed !important; bottom: 30px !important; right: 30px !important; background-color: rgba(30, 41, 59, 0.95) !important;
            padding: 16px !important; border-radius: 12px !important; box-shadow: 0 10px 30px rgba(0,0,0,0.3) !important; backdrop-filter: blur(10px) !important;
            z-index: 100000 !important; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
            color: white !important; display: flex !important; flex-direction: column !important; gap: 12px !important; user-select: none !important;
            border: 1px solid rgba(255,255,255,0.1) !important; box-sizing: border-box !important; margin: 0 !important; width: 280px !important;
        }
        .geek-row { display: flex !important; gap: 8px !important; align-items: center !important; justify-content: space-between !important; }

        .geek-select {
            background-color: rgba(0,0,0,0.4) !important; border: 1px solid rgba(255,255,255,0.2) !important;
            color: white !important; padding: 6px 8px !important; border-radius: 6px !important; outline: none !important;
            width: 100% !important; max-width: 190px !important; font-size: 13px !important; cursor: pointer !important; box-sizing: border-box !important; height: auto !important;
        }

        .geek-btn {
            background-color: rgba(255,255,255,0.1) !important; border: 1px solid transparent !important;
            color: white !important; padding: 8px 14px !important; border-radius: 6px !important;
            cursor: pointer !important; font-size: 14px !important; transition: background-color 0.2s ease !important;
            display: flex !important; align-items: center !important; gap: 6px !important; flex: 1 !important; justify-content: center !important;
            box-sizing: border-box !important; margin: 0 !important; line-height: 1.2 !important; height: auto !important;
        }
        .geek-btn:hover { background-color: rgba(255,255,255,0.2) !important; }
        .geek-btn.active { background-color: rgba(52, 152, 219, 0.8) !important; }
        .geek-btn.danger { background-color: rgba(231, 76, 60, 0.8) !important; }
        .geek-btn.danger:hover { background-color: rgba(192, 57, 43, 1) !important; }

        body.geek-alt-mode p:hover, body.geek-alt-mode li:hover, body.geek-alt-mode h1:hover, body.geek-alt-mode h2:hover,
        body.geek-alt-mode h3:hover, body.geek-alt-mode blockquote:hover {
            outline: 2px dashed #e74c3c !important; background-color: rgba(231, 76, 60, 0.08) !important; cursor: crosshair !important; border-radius: 4px !important;
        }

        /* 生词本 UI 样式 */
        #geek-vocab-notebook {
            position: fixed !important; top: 20px !important; right: 30px !important; width: 280px !important;
            max-height: 500px !important; background-color: rgba(15, 23, 42, 0.95) !important; border-radius: 12px !important;
            box-shadow: 0 10px 30px rgba(0,0,0,0.4) !important; backdrop-filter: blur(10px) !important; z-index: 100000 !important;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important; color: white !important;
            display: flex !important; flex-direction: column !important; border: 2px dashed rgba(255,255,255,0.2) !important;
            box-sizing: border-box !important; transition: border-color 0.3s ease, transform 0.2s ease !important;
        }
        #geek-vocab-notebook.drag-over { border-color: #3498db !important; background-color: rgba(41, 128, 185, 0.3) !important; transform: scale(1.02) !important; }
        .vocab-header { padding: 12px 16px !important; border-bottom: 1px solid rgba(255,255,255,0.1) !important; display: flex !important; justify-content: space-between !important; align-items: center !important; font-size: 14px !important; font-weight: bold !important; }
        .vocab-list { flex: 1 !important; overflow-y: auto !important; padding: 8px !important; margin: 0 !important; list-style: none !important; }
        .vocab-list::-webkit-scrollbar { width: 6px; }
        .vocab-list::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.2); border-radius: 3px; }
        .vocab-item { display: flex !important; justify-content: space-between !important; align-items: center !important; padding: 8px 10px !important; background: rgba(255,255,255,0.05) !important; margin-bottom: 6px !important; border-radius: 6px !important; font-size: 13px !important; }
        .vocab-item:hover { background: rgba(255,255,255,0.1) !important; }
        .vocab-word { font-weight: bold !important; color: #3498db !important; margin-right: 6px !important; cursor: pointer !important; text-decoration: underline dashed rgba(52, 152, 219, 0.5) !important; text-underline-offset: 3px !important; transition: color 0.2s !important; }
        .vocab-word:hover { color: #2ecc71 !important; text-decoration-color: #2ecc71 !important; }
        .vocab-trans { color: #bdc3c7 !important; flex: 1 !important; white-space: nowrap !important; overflow: hidden !important; text-overflow: ellipsis !important; }
        .vocab-delete { cursor: pointer !important; color: #e74c3c !important; opacity: 0.6 !important; padding: 0 4px !important; }
        .vocab-delete:hover { opacity: 1 !important; }
        .vocab-empty { text-align: center !important; padding: 30px 0 !important; color: rgba(255,255,255,0.4) !important; font-size: 13px !important; pointer-events: none;}
        .vocab-action { font-size: 12px !important; color: #95a5a6 !important; cursor: pointer !important; font-weight: normal !important; }
        .vocab-action:hover { color: white !important; }

        .vocab-category-divider {
            display: flex !important; align-items: center !important; gap: 8px !important; padding: 8px 10px 4px !important; margin-bottom: 4px !important; margin-top: 2px !important;
            font-size: 11px !important; font-weight: bold !important; letter-spacing: 0.5px !important; color: rgba(255,255,255,0.5) !important; user-select: none !important;
        }
        .vocab-category-divider::after { content: '' !important; flex: 1 !important; height: 1px !important; background: linear-gradient(to right, rgba(255,255,255,0.15), transparent) !important; }
        .vocab-category-divider.current-page { color: #2ecc71 !important; }
        .vocab-category-divider.current-page::after { background: linear-gradient(to right, rgba(46, 204, 113, 0.3), transparent) !important; }
        .vocab-category-divider.other-pages { color: #95a5a6 !important; }
        .vocab-item.on-current-page { border-left: 3px solid #2ecc71 !important; padding-left: 7px !important; }
        .vocab-item.on-current-page .vocab-word { color: #2ecc71 !important; text-decoration-color: rgba(46, 204, 113, 0.5) !important; }
        .vocab-count-badge { display: inline-block !important; background: rgba(255,255,255,0.1) !important; padding: 1px 6px !important; border-radius: 8px !important; font-size: 10px !important; font-weight: normal !important; margin-left: 4px !important; }
    `;
    document.head.appendChild(style);

    // === 第二步：气泡 DOM 重构 ===
    function buildBubbles() {
        document.querySelectorAll('strong, em').forEach(wordNode => {
            wordNode.setAttribute('draggable', 'true');
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
    setTimeout(() => { buildBubbles(); if (typeof renderVocab === 'function') renderVocab(); }, 500);
    setTimeout(() => { buildBubbles(); if (typeof renderVocab === 'function') renderVocab(); }, 1500);

    let bubbleDebounceTimer = null;
    let observer = new MutationObserver((mutations) => {
        let shouldUpdate = false;
        for (let m of mutations) {
            let target = m.target;
            if (target && target.nodeType === Node.TEXT_NODE) target = target.parentElement;

            if (target && target.closest && (target.closest('#geek-vocab-notebook') || target.closest('#geek-tts-panel'))) {
                continue;
            }
            if (m.type === 'childList' && m.addedNodes.length > 0) {
                shouldUpdate = true;
                break;
            }
        }

        if (shouldUpdate) {
            clearTimeout(bubbleDebounceTimer);
            bubbleDebounceTimer = setTimeout(() => {
                buildBubbles();
                if (typeof renderVocab === 'function') renderVocab();
            }, 300);
        }
    });
    observer.observe(document.body, { childList: true, subtree: true });

    // === 第三步：构建所有 UI ===
    let oldNotebook = document.getElementById('geek-vocab-notebook'); if (oldNotebook) oldNotebook.remove();
    let oldPanel = document.getElementById('geek-tts-panel'); if (oldPanel) oldPanel.remove();

    let notebook = document.createElement('div');
    notebook.id = 'geek-vocab-notebook';
    notebook.innerHTML = `
        <div class="vocab-header">
            <span>📥 拖拽生词本</span>
            <div><span class="vocab-action" id="geek-vocab-copy" title="复制全部到剪贴板">复制</span> | <span class="vocab-action" id="geek-vocab-clear" title="清空生词本">清空</span></div>
        </div>
        <ul class="vocab-list" id="geek-vocab-list"></ul>
    `;
    document.body.appendChild(notebook);

    let panel = document.createElement('div');
    panel.id = 'geek-tts-panel';
    panel.innerHTML = `
        <div class="geek-row">
            <span style="font-size: 13px; opacity: 0.8;">声音</span>
            <select id="geek-voice-select" class="geek-select"><option>加载语音中...</option></select>
        </div>
        <div class="geek-row">
            <button id="geek-btn-play" class="geek-btn">▶️ 全文朗读</button>
            <button id="geek-btn-stop" class="geek-btn danger">⏹ 停止</button>
        </div>
        <div style="font-size: 11px; opacity: 0.5; text-align: center; margin-top: -4px;">Alt/Cmd 空降 | Tab 切换 | R 重读</div>
    `;
    document.body.appendChild(panel);

    let voiceSelect = document.getElementById('geek-voice-select');
    let btnPlay = document.getElementById('geek-btn-play');
    let btnStop = document.getElementById('geek-btn-stop');

    // === 第四步：加载语音库 ===
    let globalVoices = [];
    let userSelectedVoiceName = null;

    voiceSelect.addEventListener('change', () => {
        if (globalVoices.length > 0) userSelectedVoiceName = globalVoices[voiceSelect.value].name;
    });

    function loadVoices() {
        let voices = window.speechSynthesis.getVoices();
        if (voices.length === 0) return;
        globalVoices = voices.filter(v => v.lang.includes('zh') || v.lang.includes('en')).sort((a, b) => (b.name.includes('Natural') ? 1 : 0) - (a.name.includes('Natural') ? 1 : 0));
        voiceSelect.innerHTML = '';
        globalVoices.forEach((voice, index) => {
            let option = document.createElement('option'); option.value = index;
            let displayName = voice.name.replace('Microsoft', '').replace('Online (Natural)', '🌟自然').trim();
            option.textContent = `${displayName} (${voice.lang})`;
            if (userSelectedVoiceName) { if (voice.name === userSelectedVoiceName) option.selected = true; }
            else { if (voice.name.includes('Xiaoxiao Online (Natural)')) option.selected = true; }
            voiceSelect.appendChild(option);
        });
    }
    window.speechSynthesis.onvoiceschanged = loadVoices; loadVoices();

    // === 生词本 LocalStorage 与拖拽逻辑 ===
    let vocabData = JSON.parse(localStorage.getItem('geek-vocab-data')) || [];
    let listEl = document.getElementById('geek-vocab-list');

    function getCurrentPageWords() {
        let pageWords = new Set();
        document.querySelectorAll('strong, em').forEach(el => {
            let word = el.childNodes[0] && el.childNodes[0].nodeType === Node.TEXT_NODE ? el.childNodes[0].textContent.trim() : el.textContent.replace(/\(.*?\)/g, '').trim();
            if (word) pageWords.add(word.toLowerCase());
        });
        return pageWords;
    }

    function renderVocab() {
        listEl.innerHTML = '';
        if (vocabData.length === 0) { listEl.innerHTML = '<div class="vocab-empty">把网页里的重点词<br>直接拖拽到这里 📥</div>'; return; }

        let pageWords = getCurrentPageWords();
        let onPageItems = [], otherItems = [];
        vocabData.forEach((item, index) => {
            let entry = { ...item, originalIndex: index };
            if (pageWords.has(item.word.toLowerCase())) onPageItems.push(entry); else otherItems.push(entry);
        });

        if (onPageItems.length > 0) {
            let divider = document.createElement('div'); divider.className = 'vocab-category-divider current-page'; divider.innerHTML = `📍 当前页面生词<span class="vocab-count-badge">${onPageItems.length}</span>`; listEl.appendChild(divider);
            onPageItems.forEach(item => {
                let li = document.createElement('li'); li.className = 'vocab-item on-current-page';
                li.innerHTML = `<div><span class="vocab-word" title="点击发音">${item.word}</span><span class="vocab-trans">${item.trans}</span></div><span class="vocab-delete" data-index="${item.originalIndex}">✖</span>`; listEl.appendChild(li);
            });
        }

        if (otherItems.length > 0) {
            let divider = document.createElement('div'); divider.className = 'vocab-category-divider other-pages'; divider.innerHTML = `📚 其他生词<span class="vocab-count-badge">${otherItems.length}</span>`; listEl.appendChild(divider);
            otherItems.forEach(item => {
                let li = document.createElement('li'); li.className = 'vocab-item';
                li.innerHTML = `<div><span class="vocab-word" title="点击发音">${item.word}</span><span class="vocab-trans">${item.trans}</span></div><span class="vocab-delete" data-index="${item.originalIndex}">✖</span>`; listEl.appendChild(li);
            });
        }
    }
    function saveVocab() { localStorage.setItem('geek-vocab-data', JSON.stringify(vocabData)); renderVocab(); }
    renderVocab();

    listEl.addEventListener('click', (e) => {
        if (e.target.classList.contains('vocab-delete')) { let idx = e.target.getAttribute('data-index'); vocabData.splice(idx, 1); saveVocab(); }
    });

    document.getElementById('geek-vocab-clear').addEventListener('click', () => { if (confirm('确定要清空所有生词吗？')) { vocabData = []; saveVocab(); } });
    document.getElementById('geek-vocab-copy').addEventListener('click', () => {
        if (vocabData.length === 0) { alert('生词本为空，没有可复制的内容。'); return; }
        let textToCopy = vocabData.map(i => `${i.word} ${i.trans}`).join('\n');
        let textarea = document.createElement('textarea'); textarea.value = textToCopy; textarea.style.cssText = 'position:fixed;left:-9999px;top:-9999px;opacity:0;'; document.body.appendChild(textarea); textarea.select();
        try { document.execCommand('copy'); alert(`已复制全部 ${vocabData.length} 个生词到剪贴板！`); }
        catch(err) { navigator.clipboard.writeText(textToCopy).then(() => alert(`已复制全部 ${vocabData.length} 个生词到剪贴板！`)).catch(() => alert('复制失败，请手动复制。')); }
        document.body.removeChild(textarea);
    });

    let dragPayload = null;
    document.addEventListener('dragstart', (e) => {
        let target = e.target;
        if (target && target.nodeType === Node.TEXT_NODE) target = target.parentElement;
        if (target && target.closest) target = target.closest('strong, em'); else target = null;
        if (target) {
            let word = target.childNodes[0] && target.childNodes[0].nodeType === Node.TEXT_NODE ? target.childNodes[0].textContent.trim() : target.textContent.replace(/\(.*?\)/g, '').trim();
            let transBubble = target.querySelector('.translation-bubble');
            let trans = transBubble ? transBubble.textContent.trim() : '';
            dragPayload = { word, trans };
            try { e.dataTransfer.setData('text/plain', JSON.stringify(dragPayload)); } catch(err) { }
            e.dataTransfer.effectAllowed = 'copy';
        }
    });

    function handleDragOver(e) { e.preventDefault(); e.dataTransfer.dropEffect = 'copy'; notebook.classList.add('drag-over'); }
    function handleDragLeave(e) { if (!notebook.contains(e.relatedTarget)) { notebook.classList.remove('drag-over'); } }
    function handleDrop(e) {
        e.preventDefault(); e.stopPropagation(); notebook.classList.remove('drag-over');
        let data = null; try { let raw = e.dataTransfer.getData('text/plain'); if (raw) data = JSON.parse(raw); } catch(err) { }
        if (!data || !data.word) data = dragPayload;
        if (data && data.word) {
            if (!vocabData.some(item => item.word === data.word)) { vocabData.unshift(data); saveVocab(); }
            else { notebook.style.borderColor = '#f1c40f'; setTimeout(() => notebook.style.borderColor = 'rgba(255,255,255,0.2)', 500); }
        }
        dragPayload = null;
    }
    notebook.addEventListener('dragover', handleDragOver); notebook.addEventListener('dragleave', handleDragLeave); notebook.addEventListener('drop', handleDrop);


    // === 第五步：音画同步核心追踪引擎 ===
    let markers = [], fullCleanText = "", globalTextOffset = 0, currentActiveBubble = null, currentWordElement = null, currentWordString = null;
    function clearActiveBubble() { if (currentActiveBubble) { currentActiveBubble.classList.remove('force-show'); currentActiveBubble = null; } }

    function preparePlaybackData(targetBlock = null) {
        let originalTargets = document.querySelectorAll('strong, em');
        if (targetBlock) targetBlock.setAttribute('data-geek-start', 'true');

        let cloneBody = document.body.cloneNode(true);

        let UI_To_Destroy = cloneBody.querySelectorAll('#geek-tts-panel, #geek-vocab-notebook, .translation-bubble, script, style');
        UI_To_Destroy.forEach(el => el.remove());

        let clonedTargets = cloneBody.querySelectorAll('strong, em');
        clonedTargets.forEach((el, index) => el.insertAdjacentText('afterbegin', `\u200B__TTS_${index}__\u200B`));

        if (targetBlock) {
            let clonedStart = cloneBody.querySelector('[data-geek-start="true"]');
            if (clonedStart) clonedStart.insertAdjacentText('afterbegin', '\u200B__START__\u200B');
            targetBlock.removeAttribute('data-geek-start');
        }

        let rawText = cloneBody.innerText || cloneBody.textContent;
        let cleanText = "", regex = /\u200B__(TTS_\d+|START)__\u200B/g, match, lastIndex = 0, startOffset = 0;
        markers = [];

        while ((match = regex.exec(rawText)) !== null) {
            cleanText += rawText.substring(lastIndex, match.index);
            if (match[1] === 'START') { startOffset = cleanText.length; }
            else {
                let targetIndex = parseInt(match[1].replace('TTS_', ''));
                let originalEl = originalTargets[targetIndex];
                if (originalEl && originalEl.querySelector('.translation-bubble')) {
                    let wordLength = originalEl.childNodes[0].textContent.trim().length;
                    markers.push({ bubble: originalEl.querySelector('.translation-bubble'), start: cleanText.length, end: cleanText.length + wordLength });
                }
            }
            lastIndex = regex.lastIndex;
        }
        cleanText += rawText.substring(lastIndex); fullCleanText = cleanText; globalTextOffset = startOffset;
        return startOffset;
    }

    // === 第六步：状态机 ===
    let currentState = 'idle', currentUtterance = null, remainingText = "", lastCharIndex = 0;
    function resetPlayerState() { currentState = 'idle'; btnPlay.innerHTML = '▶️ 全文朗读'; btnPlay.classList.remove('active'); remainingText = ""; lastCharIndex = 0; clearActiveBubble(); }

    function startPlayback(textToPlay) {
        if (!textToPlay || !textToPlay.trim()) { resetPlayerState(); return; }
        remainingText = textToPlay; lastCharIndex = 0;
        currentUtterance = new SpeechSynthesisUtterance(remainingText);
        if (globalVoices.length > 0) currentUtterance.voice = globalVoices[voiceSelect.value];
        currentUtterance.rate = 1.0;

        currentUtterance.onboundary = (e) => {
            lastCharIndex = e.charIndex; let absIndex = globalTextOffset + e.charIndex;
            let activeMarker = markers.find(m => absIndex >= m.start - 2 && absIndex <= m.end + 2);
            if (activeMarker) {
                if (currentActiveBubble !== activeMarker.bubble) {
                    clearActiveBubble(); currentActiveBubble = activeMarker.bubble; currentActiveBubble.classList.add('force-show');
                    let wordEl = currentActiveBubble.parentElement;
                    if (wordEl) { let rect = wordEl.getBoundingClientRect(); if (rect.bottom > window.innerHeight * 0.82) { window.scrollBy({ top: window.innerHeight * 0.65, behavior: 'smooth' }); } }
                }
            } else { clearActiveBubble(); }
        };
        currentUtterance.onstart = () => { currentState = 'playing'; btnPlay.innerHTML = '⏸ 暂停'; btnPlay.classList.add('active'); };
        currentUtterance.onend = () => { if (currentState === 'playing') resetPlayerState(); };
        window.speechSynthesis.speak(currentUtterance);
    }

    btnPlay.addEventListener('click', () => {
        if (currentState === 'idle') { window.speechSynthesis.cancel(); preparePlaybackData(); startPlayback(fullCleanText); }
        else if (currentState === 'playing') { window.speechSynthesis.pause(); currentState = 'paused'; btnPlay.innerHTML = '▶️ 继续'; btnPlay.classList.remove('active'); }
        else if (currentState === 'paused') { window.speechSynthesis.resume(); currentState = 'playing'; btnPlay.innerHTML = '⏸ 暂停'; btnPlay.classList.add('active'); }
        else if (currentState === 'manual_standby') { window.speechSynthesis.cancel(); startPlayback(remainingText); }
    });
    btnStop.addEventListener('click', () => { currentState = 'idle'; window.speechSynthesis.cancel(); resetPlayerState(); });

    function triggerWordPlayback(targetEl, specificWordStr = null) {
        currentWordString = specificWordStr;
        
        if (currentState === 'playing' || currentState === 'paused') {
            globalTextOffset += lastCharIndex; remainingText = remainingText.substring(lastCharIndex);
            currentState = 'manual_standby'; btnPlay.innerHTML = '▶️ 继续'; btnPlay.classList.remove('active');
        }
        window.speechSynthesis.cancel(); clearActiveBubble();
        let word = specificWordStr, textToSpeak = word;

        if (targetEl) {
            currentWordElement = targetEl;
            if (!word) { let clone = targetEl.cloneNode(true); let b = clone.querySelector('.translation-bubble'); if (b) b.remove(); word = clone.textContent.trim(); textToSpeak = word; currentWordString = word; }
            let bubble = targetEl.querySelector('.translation-bubble');
            if (bubble) {
                currentActiveBubble = bubble; bubble.classList.add('force-show');
                let rawTransText = bubble.textContent;
                let transText = rawTransText.replace(/[\(\)]/g, '').replace(/\bv\./g, '动词 ').replace(/\bn\./g, '名词 ').replace(/\badj\./g, '形容词 ').replace(/\badv\./g, '副词 ').replace(/\bprep\./g, '介词 ').replace(/\bconj\./g, '连词 ').replace(/\bpron\./g, '代词 ');
                textToSpeak = word + "，" + transText;
            }
            targetEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
            let sel = window.getSelection(); sel.removeAllRanges(); let range = document.createRange();
            if (targetEl.firstChild && targetEl.firstChild.nodeType === Node.TEXT_NODE) range.selectNodeContents(targetEl.firstChild); else range.selectNodeContents(targetEl);
            sel.addRange(range);
        } else { currentWordElement = null; }

        if(textToSpeak) {
            let utterance = new SpeechSynthesisUtterance(textToSpeak);
            if (globalVoices.length > 0) utterance.voice = globalVoices[voiceSelect.value];
            utterance.rate = textToSpeak === word ? 0.9 : 1.0;
            window.speechSynthesis.speak(utterance);
        }
    }

    // === 第七步：点击分发 ===
    document.addEventListener('click', function(e) {
        let target = e.target;
        if (target && target.nodeType === Node.TEXT_NODE) target = target.parentElement; 

        if (target && target.classList && target.classList.contains('vocab-word')) {
            let word = target.textContent.trim();
            let vocabItem = target.closest('.vocab-item');
            let isOnCurrentPage = vocabItem && vocabItem.classList.contains('on-current-page');

            if (isOnCurrentPage) {
                let matchedEl = null;
                document.querySelectorAll('strong, em').forEach(el => {
                    if (matchedEl) return;
                    let elWord = el.childNodes[0] && el.childNodes[0].nodeType === Node.TEXT_NODE ? el.childNodes[0].textContent.trim() : '';
                    if (elWord.toLowerCase() === word.toLowerCase()) matchedEl = el;
                });
                if (matchedEl) { triggerWordPlayback(matchedEl, word); return; }
            }

            if (currentState === 'playing' || currentState === 'paused') {
                globalTextOffset += lastCharIndex; remainingText = remainingText.substring(lastCharIndex);
                currentState = 'manual_standby'; btnPlay.innerHTML = '▶️ 继续'; btnPlay.classList.remove('active');
            }
            window.speechSynthesis.cancel(); clearActiveBubble();

            currentWordString = word; 
            currentWordElement = null; 

            let utterance = new SpeechSynthesisUtterance(word);
            let enVoice = globalVoices.find(v => v.name.includes('Aria Online (Natural)')) || globalVoices.find(v => v.name.includes('Jenny Online (Natural)'));
            if (enVoice) utterance.voice = enVoice; else utterance.voice = globalVoices[voiceSelect.value];
            utterance.rate = 1.0; window.speechSynthesis.speak(utterance); return;
        }

        if (target && target.closest && (target.closest('#geek-tts-panel') || target.closest('#geek-vocab-notebook'))) return;

        if (e.altKey || e.metaKey) {
            let targetBlock = target.closest ? target.closest('p, li, h1, h2, h3, h4, h5, h6, blockquote') : null;
            if (targetBlock) {
                e.preventDefault(); e.stopPropagation();
                window.speechSynthesis.cancel(); resetPlayerState();
                let startOffset = preparePlaybackData(targetBlock);
                startPlayback(fullCleanText.substring(startOffset)); return;
            }
        }

        if (['INPUT', 'TEXTAREA', 'BUTTON', 'A', 'SELECT', 'OPTION'].includes(target.tagName)) return;

        let range; if (document.caretRangeFromPoint) range = document.caretRangeFromPoint(e.clientX, e.clientY);
        if (range && range.startContainer.nodeType === Node.TEXT_NODE) {
            let node = range.startContainer, offset = range.startOffset, text = node.textContent;
            let start = offset; while (start > 0 && /\w/.test(text[start - 1])) { start--; }
            let end = offset; while (end < text.length && /\w/.test(text[end])) { end++; }
            let word = text.slice(start, end).trim();

            if (word && /^[a-zA-Z]+$/.test(word)) {
                let parentEl = node.parentElement; let targetEl = parentEl ? parentEl.closest('strong, em') : null;
                if (!targetEl) { let selectRange = document.createRange(); selectRange.setStart(node, start); selectRange.setEnd(node, end); let sel = window.getSelection(); sel.removeAllRanges(); sel.addRange(selectRange); }
                triggerWordPlayback(targetEl, word);
            }
        }
    });

    // === 第八步：键盘状态监听 ===
    document.addEventListener('keydown', function(e) {
        if (['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName)) return;

        if (e.key === 'Alt' || e.key === 'Meta') document.body.classList.add('geek-alt-mode');
        
        if (e.key === 'Tab') {
            let allWords = Array.from(document.querySelectorAll('strong, em'));
            if (allWords.length === 0) return;
            e.preventDefault(); let nextIndex = 0;
            if (currentWordElement) { let currentIndex = allWords.indexOf(currentWordElement); if (currentIndex !== -1) { if (e.shiftKey) nextIndex = (currentIndex - 1 + allWords.length) % allWords.length; else nextIndex = (currentIndex + 1) % allWords.length; } }
            triggerWordPlayback(allWords[nextIndex], null);
        }

        // 【核心修复：防冲突】如果按了 Cmd(Meta), Ctrl 或 Alt，坚决不拦截 R 键，放行给浏览器处理系统快捷键！
        if (e.key.toLowerCase() === 'r' && !e.metaKey && !e.ctrlKey && !e.altKey) {
            if (currentWordElement || currentWordString) {
                e.preventDefault();
                triggerWordPlayback(currentWordElement, currentWordString);
            }
        }
    });
    
    document.addEventListener('keyup', function(e) { if (e.key === 'Alt' || e.key === 'Meta') document.body.classList.remove('geek-alt-mode'); });

})();