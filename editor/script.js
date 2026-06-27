const ws = new WebSocket('ws://localhost:8081');
ws.onopen = () => console.log("Verbonden met Bridge!");

// ---- GLOBAL STATE ----
const totalTimeMs = (1 * 3600 + 36 * 60 + 32) * 1000; 
let zoomStartMs = 0;
let zoomEndMs = 60000; 
const fps = 23.98; 
const frameMs = 1000 / fps; 
let playheadMs = 0;
const TRACK_HEIGHT = 80;
let selectedTrackId = 'wind';
let selectedItemId = null; 

let settings = { minDistMs: 50 };
let lastVolume = 100;
let isMuted = false;

let historyStack = [];
let historyIndex = -1;

const tracksDef = [
    { id: 'wind', name: 'Wind', icon: 'fa-fan', color: '#00d2ff', type: 'continuous', magnet: null, showLabels: true },
    { id: 'lightning', name: 'Bliksem', icon: 'fa-bolt', color: '#f1c40f', type: 'block', magnet: null, showLabels: true },
    { id: 'color', name: 'Kleur', icon: 'fa-lightbulb', color: '#ff4757', type: 'continuous', magnet: null, showLabels: true },
    { id: 'fire', name: 'Vuur', icon: 'fa-fire', color: '#e67e22', type: 'continuous', magnet: null, showLabels: true },
    { id: 'movieinfo', name: 'Movie Info', icon: 'fa-clapperboard', color: '#9b59b6', type: 'block', magnet: null, showLabels: true },
    { id: 'playlist', name: 'Segment', icon: 'fa-film', color: '#2ecc71', type: 'block', magnet: null, showLabels: true }
];

const movieInfoPresets = [
    { id: 'START', text: 'START', tip: 'Use this if there a lot of black frames of nothing at the start of the videofile', multi: false },
    { id: 'BRANDINTRO', text: 'BRANDINTRO', tip: 'Start of Brand intro\'s', multi: false },
    { id: 'BRANDEND', text: 'BRANDEND', tip: 'End of Brand intro\'s', multi: false },
    { id: 'STARTMOVIE', text: '*STARTMOVIE', tip: 'Where the movie actually starts', multi: false },
    { id: 'MOVIEINTRO', text: 'MOVIEINTRO', tip: 'Where the movie intro starts', multi: false },
    { id: 'MOVIEINTROEND', text: 'MOVIEINTROEND', tip: 'Where the movie intro ends', multi: false },
    { id: 'PAUSE', text: '*PAUSE', tip: 'The best moment for a break in the movie', multi: true },
    { id: 'RESUME', text: '*RESUME', tip: 'The best moment where the movie picks up again', multi: true },
    { id: 'CREDITS', text: 'CREDITS', tip: 'Where the credits begin', multi: false },
    { id: 'AFTERMOVIESTART', text: 'AFTERMOVIESTART', tip: 'Where the Aftermovie starts', multi: false },
    { id: 'AFTERMOVIEEND', text: 'AFTERMOVIEEND', tip: 'Where the Aftermovie ends', multi: false },
    { id: 'ENDCREDITS', text: '**ENDCREDITS', tip: 'Where the end-credits start and it\'s not worth watching more', multi: false }
];

const colorGridHexes = [
    '#ff0000', '#ff8800', '#ffff00', '#88ff00', '#00ff00', '#00ff88', '#00ffff', '#0088ff', '#0000ff', '#8800ff', '#ff00ff', '#ff0088',
    '#ffffff', '#cccccc', '#999999', '#666666', '#333333', '#000000', '#8b4513', '#d2b48c', '#ffe4c4', '#ffb6c1', '#dda0dd', '#4b0082'
];

let dataPoints = [];
let dataBlocks = [];

function saveState() {
    if (historyIndex < historyStack.length - 1) historyStack = historyStack.slice(0, historyIndex + 1);
    historyStack.push({ points: JSON.parse(JSON.stringify(dataPoints)), blocks: JSON.parse(JSON.stringify(dataBlocks)) });
    if (historyStack.length > 100) historyStack.shift(); else historyIndex++;
}
function undo() {
    if (historyIndex > 0) {
        historyIndex--; dataPoints = JSON.parse(JSON.stringify(historyStack[historyIndex].points)); dataBlocks = JSON.parse(JSON.stringify(historyStack[historyIndex].blocks));
        selectedItemId = null; renderAll();
    }
}
function redo() {
    if (historyIndex < historyStack.length - 1) {
        historyIndex++; dataPoints = JSON.parse(JSON.stringify(historyStack[historyIndex].points)); dataBlocks = JSON.parse(JSON.stringify(historyStack[historyIndex].blocks));
        selectedItemId = null; renderAll();
    }
}
saveState();

// ---- DOM ELEMENTS ----
const dawWorkspace = document.getElementById('daw-workspace');
const trackLanes = document.getElementById('track-lanes');
const rulerCanvas = document.getElementById('ruler-canvas');
const ctxR = rulerCanvas.getContext('2d');
const autoCanvas = document.getElementById('automation-canvas');
const ctxA = autoCanvas.getContext('2d');
const masterCanvas = document.getElementById('master-canvas');
const ctxM = masterCanvas.getContext('2d');
const zoomWindow = document.getElementById('zoom-window');
const playheadEl = document.getElementById('playhead');
const masterPlayheadEl = document.getElementById('master-playhead');
const contextBar = document.getElementById('context-items');
const btnTrash = document.getElementById('btn-trash');
const volumeSlider = document.getElementById('volume-slider');
const btnMute = document.getElementById('btn-mute');
const cMenu = document.getElementById('point-context-menu');

// Setup Tracks
const headersContainer = document.getElementById('track-headers');
tracksDef.forEach((track, index) => {
    const header = document.createElement('div');
    header.className = 'track-header';
    header.id = `header-${track.id}`;
    header.innerHTML = `
        <div class="track-icon" style="color: ${track.color};"><i class="fas ${track.icon}"></i></div>
        <div class="track-info">
            <div class="track-title">${track.name} <span style="font-size:10px; color:#666">[${track.name.charAt(0).toUpperCase()}]</span></div>
            <div class="track-status">Wait...</div>
        </div>
        <div class="track-controls">
            <button class="btn-tiny btn-magnet-track" id="mag-${track.id}" title="Magnet Snap">F</button>
            <button class="btn-tiny btn-settings-track" id="set-${track.id}" title="Settings"><i class="fas fa-cog"></i></button>
            <button class="btn-tiny btn-solo" title="Solo">S</button>
            <button class="btn-tiny btn-mute" title="Mute">M</button>
        </div>
    `;
    headersContainer.appendChild(header);
    
    header.addEventListener('click', (e) => {
        if(!e.target.closest('button')) selectTrack(track.id);
    });
    
    document.getElementById(`mag-${track.id}`).addEventListener('click', (e) => {
        const states = [null, 2, 4, 6, 12];
        const curIdx = states.indexOf(track.magnet);
        track.magnet = states[(curIdx + 1) % states.length];
        e.currentTarget.innerText = track.magnet === null ? 'F' : track.magnet;
        e.currentTarget.classList.toggle('active', track.magnet !== null);
        if(selectedTrackId === track.id) updateContextTools(track);
    });
    
    document.getElementById(`set-${track.id}`).addEventListener('click', (e) => {
        document.getElementById('modal-track-title').innerText = `${track.name} Settings`;
        document.getElementById('setting-track-labels').checked = track.showLabels;
        document.getElementById('setting-track-labels').onchange = (ev) => {
            track.showLabels = ev.target.checked; renderAll();
        };
        document.getElementById('modal-overlay').style.display = 'block';
        document.getElementById('modal-track-settings').style.display = 'block';
    });

    const lane = document.createElement('div');
    lane.className = 'track-lane';
    lane.id = `lane-${track.id}`;
    trackLanes.appendChild(lane);
    
    track.yPos = index * TRACK_HEIGHT;
});

autoCanvas.style.height = (tracksDef.length * TRACK_HEIGHT) + 'px';
selectTrack('wind');

function selectTrack(trackId) {
    selectedTrackId = trackId;
    document.querySelectorAll('.track-header').forEach(h => h.classList.remove('selected'));
    const header = document.getElementById(`header-${trackId}`);
    if (header) header.classList.add('selected');
    const track = tracksDef.find(t => t.id === trackId);
    updateContextTools(track);
}

function updateContextTools(track) {
    contextBar.innerHTML = '';
    if(!track) return;
    
    if (track.id === 'movieinfo') {
        movieInfoPresets.forEach(preset => {
            const btn = document.createElement('div'); btn.className = 'preset-btn';
            btn.style.backgroundColor = track.color; btn.style.height = '30px'; btn.style.width = 'auto'; btn.style.padding = '5px 10px';
            btn.innerHTML = `${preset.text} <div class="tooltip">${preset.tip}</div>`;
            
            if(!preset.multi && dataBlocks.some(b => b.trackId === 'movieinfo' && b.text === preset.id)) {
                btn.setAttribute('disabled', 'true');
            } else {
                btn.onclick = () => { addBlock(track.id, playheadMs, 1000, 100, preset.id); updateContextTools(track); };
            }
            contextBar.appendChild(btn);
        });
    } else if (track.type === 'block') {
        [1, 2, 3, 4].forEach(i => {
            const btn = document.createElement('div'); btn.className = 'preset-btn';
            btn.style.backgroundColor = track.color; btn.style.height = (i*10) + 'px';
            btn.title = `Add Flash ${i}`;
            btn.onclick = () => addBlock(track.id, playheadMs, 100 * i, 100, `Flash ${i}`);
            contextBar.appendChild(btn);
        });
    } else if (track.id === 'color') {
        const grid = document.createElement('div'); grid.className = 'color-grid-container';
        colorGridHexes.forEach(c => {
            const btn = document.createElement('div'); btn.className = 'color-grid-btn';
            btn.style.backgroundColor = c;
            btn.onclick = () => addPoint(track.id, playheadMs, 100, c);
            grid.appendChild(btn);
        });
        contextBar.appendChild(grid);
    } else {
        let allowed = [0, 1, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100];
        if(track.magnet === 2) allowed = [0, 100];
        else if(track.magnet === 4) allowed = [0, 20, 60, 100];
        else if(track.magnet === 6) allowed = [0, 20, 40, 60, 80, 100];
        else if(track.magnet === 12) allowed = [0, 1, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100];
        
        allowed.forEach(val => {
            const btn = document.createElement('div'); btn.className = 'preset-btn';
            btn.style.backgroundColor = track.color; 
            btn.style.height = Math.max(10, (val / 100) * 35) + 'px'; 
            btn.innerText = val === 0 ? 'OFF' : val;
            btn.onclick = () => addPoint(track.id, playheadMs, val);
            contextBar.appendChild(btn);
        });
    }
}

function isTooClose(trackId, ms, ignoreId = null) {
    const minDist = parseInt(settings.minDistMs);
    return dataPoints.some(p => p.trackId === trackId && p.id !== ignoreId && Math.abs(p.ms - ms) < minDist);
}

function addPoint(trackId, ms, val, colorHex=null) {
    const snap = snapMs(ms);
    const existing = dataPoints.find(p => p.trackId === trackId && p.ms === snap);
    if(existing) {
        existing.val = val;
        if(colorHex) existing.colorHex = colorHex;
        selectedItemId = existing.id;
    } else {
        if(isTooClose(trackId, snap)) return; 
        const id = Date.now();
        dataPoints.push({ id: id, trackId, ms: snap, val, colorHex });
        selectedItemId = id;
    }
    saveState(); renderAll();
}

function addBlock(trackId, ms, dur, val, text) {
    const id = Date.now();
    dataBlocks.push({ id: id, trackId, ms: snapMs(ms), dur, val, text });
    selectedItemId = id;
    saveState(); renderAll();
}

function snapMs(ms) { return Math.round(ms / frameMs) * frameMs; }
function msToPx(ms) { const w = dawWorkspace.clientWidth; return ((ms - zoomStartMs) / (zoomEndMs - zoomStartMs)) * w; }
function pxToMs(px) { const w = dawWorkspace.clientWidth; return zoomStartMs + (px / w) * (zoomEndMs - zoomStartMs); }
function formatTime(ms, showFrames=false) {
    const totalSec = Math.floor(ms / 1000);
    const h = Math.floor(totalSec / 3600); const m = Math.floor((totalSec % 3600) / 60); const s = totalSec % 60;
    let str = `${h > 0 ? h.toString().padStart(2, '0') + ':' : ''}${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
    if (showFrames) { const frame = Math.floor((ms % 1000) / frameMs); str += `:${frame.toString().padStart(2, '0')}`; }
    return str;
}

function renderAll() {
    renderMaster(); renderRuler(); renderAutomation(); renderDOM(); updatePlayheads();
}

function renderMaster() {
    masterCanvas.width = masterCanvas.clientWidth; masterCanvas.height = masterCanvas.clientHeight;
    ctxM.clearRect(0,0, masterCanvas.width, masterCanvas.height);
    const masterW = masterCanvas.width; const totalMins = Math.ceil(totalTimeMs / 60000);
    
    // Draw Ticks
    ctxM.strokeStyle = '#555'; ctxM.fillStyle = '#aaa'; ctxM.font = '10px monospace';
    for(let m = 0; m <= totalMins; m++) {
        const x = ( (m * 60000) / totalTimeMs ) * masterW;
        if (m % 10 === 0) {
            ctxM.beginPath(); ctxM.moveTo(x, 15); ctxM.lineTo(x, 35); ctxM.lineWidth = 2; ctxM.stroke();
            ctxM.fillText(`${m}m`, x + 2, 12);
        } else {
            ctxM.beginPath(); ctxM.moveTo(x, 25); ctxM.lineTo(x, 35); ctxM.lineWidth = 1; ctxM.stroke();
        }
    }
    
    // Draw mini overlapping automation
    tracksDef.filter(t => t.type === 'continuous').forEach(track => {
        const pts = dataPoints.filter(p => p.trackId === track.id).sort((a,b) => a.ms - b.ms);
        if(pts.length === 0) return;
        ctxM.beginPath();
        let currentVal = 0;
        pts.forEach(p => {
            const x = (p.ms / totalTimeMs) * masterW;
            ctxM.lineTo(x, 35 - (currentVal/100)*20);
            currentVal = p.val;
            ctxM.lineTo(x, 35 - (currentVal/100)*20);
        });
        ctxM.lineTo(masterW, 35 - (currentVal/100)*20);
        ctxM.strokeStyle = track.color + '80'; ctxM.lineWidth = 1; ctxM.stroke();
    });

    const zX = (zoomStartMs / totalTimeMs) * masterW;
    const zW = ((zoomEndMs - zoomStartMs) / totalTimeMs) * masterW;
    zoomWindow.style.left = Math.max(0, zX + 10) + 'px'; 
    zoomWindow.style.width = zW + 'px';
}

function renderRuler() {
    rulerCanvas.width = rulerCanvas.clientWidth; rulerCanvas.height = rulerCanvas.clientHeight;
    ctxR.clearRect(0, 0, rulerCanvas.width, rulerCanvas.height);
    const zoomDur = zoomEndMs - zoomStartMs; const pxPerSec = (1000 / zoomDur) * rulerCanvas.width;
    ctxR.strokeStyle = '#555'; ctxR.fillStyle = '#aaa'; ctxR.font = '10px monospace';
    
    let secInterval = 1;
    if (pxPerSec < 2) secInterval = 600; else if (pxPerSec < 10) secInterval = 60; else if (pxPerSec < 30) secInterval = 10; else if (pxPerSec < 60) secInterval = 5;
    
    for(let s = Math.floor(zoomStartMs / 1000); s <= Math.ceil(zoomEndMs / 1000); s++) {
        if(s % secInterval !== 0) continue;
        let x = msToPx(s * 1000);
        if(x >= 0 && x <= rulerCanvas.width) {
            ctxR.beginPath(); ctxR.moveTo(x, 20); ctxR.lineTo(x, 40); ctxR.lineWidth = 2; ctxR.stroke();
            ctxR.fillText(pxPerSec > 50 ? `${s % 60}s` : formatTime(s*1000), x + 3, 15);
        }
    }
    if (pxPerSec > 100) {
        ctxR.strokeStyle = '#333'; ctxR.lineWidth = 1;
        for(let f = Math.floor(zoomStartMs / frameMs); f <= Math.ceil(zoomEndMs / frameMs); f++) {
            let x = msToPx(f * frameMs);
            if(x >= 0 && x <= rulerCanvas.width) {
                ctxR.beginPath(); ctxR.moveTo(x, 30); ctxR.lineTo(x, 40); ctxR.stroke();
                if(pxPerSec > 300) ctxR.fillText(f % Math.round(fps), x+2, 38);
            }
        }
    }
}

function renderAutomation() {
    autoCanvas.width = dawWorkspace.clientWidth; autoCanvas.height = tracksDef.length * TRACK_HEIGHT;
    ctxA.clearRect(0, 0, autoCanvas.width, autoCanvas.height);
    
    tracksDef.filter(t => t.type === 'continuous').forEach(track => {
        const pts = dataPoints.filter(p => p.trackId === track.id).sort((a,b) => a.ms - b.ms);
        const yBase = track.yPos + TRACK_HEIGHT;
        
        let currentVal = 0;
        let currentColor = track.color;
        const beforePts = pts.filter(p => p.ms <= zoomStartMs);
        if(beforePts.length > 0) {
            currentVal = beforePts[beforePts.length-1].val;
            currentColor = beforePts[beforePts.length-1].colorHex || track.color;
        }
        
        const inPts = pts.filter(p => p.ms > zoomStartMs && p.ms <= zoomEndMs);
        let startX = 0;
        let lastY = yBase - (currentVal/100)*TRACK_HEIGHT;
        
        // Draw segment by segment to color correctly
        inPts.forEach(p => {
            const x = msToPx(p.ms);
            ctxA.beginPath();
            ctxA.moveTo(startX, yBase);
            ctxA.lineTo(startX, lastY);
            ctxA.lineTo(x, lastY);
            ctxA.lineTo(x, yBase);
            ctxA.closePath();
            ctxA.fillStyle = currentColor + '60'; 
            ctxA.fill();
            ctxA.strokeStyle = currentColor; ctxA.lineWidth = 2;
            ctxA.beginPath(); ctxA.moveTo(startX, lastY); ctxA.lineTo(x, lastY); ctxA.stroke();
            
            startX = x;
            currentVal = p.val;
            currentColor = p.colorHex || track.color;
            lastY = yBase - (currentVal/100)*TRACK_HEIGHT;
            ctxA.beginPath(); ctxA.moveTo(x, yBase - (p.val/100)*TRACK_HEIGHT); ctxA.lineTo(x, lastY); ctxA.stroke();
        });
        
        ctxA.beginPath();
        ctxA.moveTo(startX, yBase); ctxA.lineTo(startX, lastY); ctxA.lineTo(autoCanvas.width, lastY); ctxA.lineTo(autoCanvas.width, yBase);
        ctxA.closePath();
        ctxA.fillStyle = currentColor + '60'; ctxA.fill();
        ctxA.beginPath(); ctxA.moveTo(startX, lastY); ctxA.lineTo(autoCanvas.width, lastY); ctxA.strokeStyle = currentColor; ctxA.stroke();
    });
}

function snapIntensity(trackId, val) {
    const track = tracksDef.find(t => t.id === trackId);
    if(!track || !track.magnet) return val;
    let allowed = [];
    if(track.magnet === 2) allowed = [0, 100];
    else if(track.magnet === 4) allowed = [0, 20, 60, 100];
    else if(track.magnet === 6) allowed = [0, 20, 40, 60, 80, 100];
    else if(track.magnet === 12) allowed = [0, 1, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100];
    return allowed.reduce((prev, curr) => Math.abs(curr - val) < Math.abs(prev - val) ? curr : prev);
}

function renderDOM() {
    document.querySelectorAll('.keyframe-point, .block').forEach(el => el.remove());
    let isSelectedOnPlayhead = false;

    dataPoints.forEach(p => {
        if(p.ms < zoomStartMs || p.ms > zoomEndMs) return;
        const track = tracksDef.find(t => t.id === p.trackId);
        const lane = document.getElementById(`lane-${p.trackId}`);
        if(!lane) return;
        
        const el = document.createElement('div');
        el.className = 'keyframe-point';
        if(selectedItemId === p.id) { el.classList.add('selected'); if(p.ms === snapMs(playheadMs)) isSelectedOnPlayhead = true; }
        
        el.style.left = msToPx(p.ms) + 'px';
        const yPx = p.val === 0 ? TRACK_HEIGHT - 6 : TRACK_HEIGHT - (p.val/100)*TRACK_HEIGHT;
        el.style.top = yPx + 'px';
        
        let iconHtml = '';
        let wrapStyle = `background-color: ${p.colorHex || track.color};`;
        if(p.val === 0) {
            iconHtml = '<i class="fas fa-ban" style="font-size:10px; color:black;"></i>';
            wrapStyle = 'background-color: red; border-color: black;';
        } else {
            if(track.id === 'wind') {
                const animDur = Math.max(0.1, 1 - (p.val/100)) + 's';
                iconHtml = `<i class="fas fa-fan anim-spin" style="font-size:10px; color:black; animation-duration:${animDur}"></i>`;
            } else if(track.id === 'fire') {
                const scale = 0.5 + (p.val/100);
                iconHtml = `<i class="fas fa-fire" style="font-size:10px; color:black; transform:scale(${scale})"></i>`;
            } else {
                iconHtml = ''; // Just color bolletje
            }
        }
        
        let labelHtml = '';
        if(track.showLabels) {
            const labelText = track.id === 'color' && p.colorHex ? `${p.val}% ${p.colorHex}` : `${p.val}%`;
            labelHtml = `<div class="point-label">${labelText}</div>`;
        }

        el.innerHTML = `${labelHtml}<div class="icon-wrap" style="${wrapStyle}">${iconHtml}</div>`;
        bindDrag(el, p, true); lane.appendChild(el);
    });
    
    dataBlocks.forEach(b => {
        if (b.ms + b.dur < zoomStartMs || b.ms > zoomEndMs) return;
        const track = tracksDef.find(t => t.id === b.trackId);
        const lane = document.getElementById(`lane-${b.trackId}`);
        if(!lane) return;
        
        const el = document.createElement('div');
        el.className = 'block';
        if(selectedItemId === b.id) { el.style.border = '2px solid white'; if(b.ms === snapMs(playheadMs)) isSelectedOnPlayhead = true; }
        
        let x = msToPx(b.ms); let w = msToPx(b.ms + b.dur) - x;
        el.style.left = x + 'px'; el.style.width = Math.max(2, w) + 'px'; el.style.backgroundColor = track.color;
        
        let icon = '';
        if(track.id === 'lightning') {
            const animDur = Math.max(0.05, 0.5 - ((b.val/100)*0.45)) + 's';
            icon = `<i class="fas fa-bolt anim-flash" style="animation-duration:${animDur}; font-size:14px;"></i>`;
        }
        
        el.innerHTML = `<div class="handle-x handle-left"></div><div class="drag-area">${icon} ${b.text}</div><div class="handle-x handle-right"></div>`;
        bindDrag(el, b, false); lane.appendChild(el);
    });
    
    if (selectedItemId && isSelectedOnPlayhead) btnTrash.removeAttribute('disabled'); else btnTrash.setAttribute('disabled', 'true');
}

// Custom Context Menu state
let cMenuTargetId = null; let floatingPoint = null;
function hideContextMenu() { cMenu.style.display = 'none'; }

function startCopyPoint(p) {
    hideContextMenu();
    const track = tracksDef.find(t => t.id === p.trackId);
    floatingPoint = document.createElement('div');
    floatingPoint.className = 'floating-point';
    floatingPoint.style.backgroundColor = p.colorHex || track.color;
    floatingPoint.dataset.trackId = p.trackId; floatingPoint.dataset.val = p.val; floatingPoint.dataset.colorHex = p.colorHex || '';
    document.body.appendChild(floatingPoint);
    
    const moveFloat = (e) => {
        floatingPoint.style.left = e.clientX + 'px'; floatingPoint.style.top = e.clientY + 'px';
        const rect = dawWorkspace.getBoundingClientRect();
        if(e.clientY >= rect.top && e.clientY <= rect.bottom) {
            const lane = document.getElementById(`lane-${p.trackId}`);
            if(lane) {
                const pctChange = -((e.clientY - lane.getBoundingClientRect().bottom) / TRACK_HEIGHT) * 100;
                floatingPoint.dataset.val = snapIntensity(p.trackId, Math.min(100, Math.max(0, Math.round(pctChange))));
            }
        }
    };
    const dropFloat = (e) => {
        window.removeEventListener('mousemove', moveFloat); window.removeEventListener('mousedown', dropFloat);
        floatingPoint.remove();
        const rect = dawWorkspace.getBoundingClientRect();
        if(e.clientX >= rect.left && e.clientX <= rect.right) {
            const ms = snapMs(pxToMs(e.clientX - rect.left));
            if(!isTooClose(floatingPoint.dataset.trackId, ms)) {
                addPoint(floatingPoint.dataset.trackId, ms, parseInt(floatingPoint.dataset.val), floatingPoint.dataset.colorHex || null);
            }
        }
        floatingPoint = null;
    };
    window.addEventListener('mousemove', moveFloat); setTimeout(() => window.addEventListener('mousedown', dropFloat), 10);
}

document.getElementById('cmenu-delete').onclick = () => {
    if(cMenuTargetId) { dataPoints = dataPoints.filter(p => p.id !== cMenuTargetId); selectedItemId = null; saveState(); renderAll(); hideContextMenu(); }
};
document.getElementById('cmenu-copy').onclick = () => {
    if(cMenuTargetId) { const p = dataPoints.find(p => p.id === cMenuTargetId); if(p) startCopyPoint(p); }
};

function bindDrag(el, dataObj, isPoint) {
    let mode = 'move'; let startX = 0, startY = 0, oMs = 0, oVal = 0, oDur = 0;
    
    el.addEventListener('mousedown', e => {
        e.stopPropagation(); selectedItemId = dataObj.id; selectTrack(dataObj.trackId); renderAll();
        if(e.button === 2) { 
            dataPoints = dataPoints.filter(p => p.id !== dataObj.id); dataBlocks = dataBlocks.filter(b => b.id !== dataObj.id);
            selectedItemId = null; saveState(); renderAll(); return;
        }
        
        startX = e.clientX; startY = e.clientY; oMs = dataObj.ms; oVal = dataObj.val; if(!isPoint) oDur = dataObj.dur;
        if(e.target.classList.contains('handle-left')) mode = 'resize-left'; else if(e.target.classList.contains('handle-right')) mode = 'resize-right'; else mode = 'move';
        let hasMoved = false;
        
        const onMove = me => {
            hasMoved = true;
            if(mode === 'move') {
                if(e.shiftKey) { 
                    dataObj.ms = oMs;
                    if(isPoint) dataObj.val = snapIntensity(dataObj.trackId, Math.min(100, Math.max(0, Math.round(oVal - ((me.clientY - startY) / TRACK_HEIGHT) * 100))));
                } else if (e.ctrlKey) { 
                    const newMs = Math.max(0, snapMs(oMs + pxToMs(me.clientX) - pxToMs(startX)));
                    if(!isTooClose(dataObj.trackId, newMs, dataObj.id)) dataObj.ms = newMs; dataObj.val = oVal;
                } else { 
                    const newMs = Math.max(0, snapMs(oMs + pxToMs(me.clientX) - pxToMs(startX)));
                    if(!isTooClose(dataObj.trackId, newMs, dataObj.id)) dataObj.ms = newMs;
                    if(isPoint) dataObj.val = snapIntensity(dataObj.trackId, Math.min(100, Math.max(0, Math.round(oVal - ((me.clientY - startY) / TRACK_HEIGHT) * 100))));
                }
            } else if (mode === 'resize-right') { dataObj.dur = Math.max(frameMs, snapMs(oDur + pxToMs(me.clientX) - pxToMs(startX))); }
            renderAll();
        };
        const onUp = (me) => { 
            window.removeEventListener('mousemove', onMove); window.removeEventListener('mouseup', onUp); 
            if(hasMoved) saveState();
            else if(e.button === 0 && isPoint) { cMenuTargetId = dataObj.id; cMenu.style.left = me.clientX + 'px'; cMenu.style.top = me.clientY + 'px'; cMenu.style.display = 'block'; }
        };
        window.addEventListener('mousemove', onMove); window.addEventListener('mouseup', onUp);
    });
}

// ---- PLAYHEAD & NAVIGATION ----
function updatePlayheads() {
    playheadEl.style.left = msToPx(playheadMs) + 'px';
    const mw = masterCanvas.clientWidth;
    masterPlayheadEl.style.left = ((playheadMs / totalTimeMs) * mw) + 10 + 'px'; 
    document.getElementById('time-display').innerText = `${formatTime(playheadMs, true)} / ${formatTime(totalTimeMs)}`;
}

dawWorkspace.addEventListener('mousedown', e => {
    hideContextMenu(); if(e.target.closest('.keyframe-point') || e.target.closest('.block')) return;
    playheadMs = Math.max(0, snapMs(pxToMs(e.clientX - dawWorkspace.getBoundingClientRect().left))); renderAll();
});
rulerCanvas.addEventListener('mousedown', e => {
    playheadMs = Math.max(0, snapMs(pxToMs(e.clientX - rulerCanvas.getBoundingClientRect().left))); renderAll();
});
masterCanvas.parentElement.addEventListener('mousedown', e => {
    if(e.target.classList.contains('handle-left') || e.target.classList.contains('handle-right') || e.target.classList.contains('zoom-window')) return;
    const mw = masterCanvas.clientWidth;
    const clickedMs = Math.max(0, snapMs(((e.clientX - 10) / mw) * totalTimeMs));
    const dur = zoomEndMs - zoomStartMs;
    zoomStartMs = Math.max(0, Math.min(totalTimeMs - dur, clickedMs - (dur/2))); zoomEndMs = zoomStartMs + dur; renderAll();
});

// ---- ZOOM & PAN CONTROLS ----
dawWorkspace.addEventListener('wheel', e => {
    e.preventDefault(); hideContextMenu(); const dur = zoomEndMs - zoomStartMs;
    if(e.ctrlKey) {
        const newDur = Math.max(1000, Math.min(totalTimeMs, dur * (e.deltaY > 0 ? 1.2 : 0.8)));
        zoomStartMs = Math.max(0, playheadMs - (newDur * ((playheadMs - zoomStartMs) / dur))); zoomEndMs = Math.min(totalTimeMs, zoomStartMs + newDur);
    } else if (e.shiftKey) {
        zoomStartMs = Math.max(0, Math.min(totalTimeMs - dur, zoomStartMs + ((dur * 0.1) * Math.sign(e.deltaY)))); zoomEndMs = zoomStartMs + dur;
    }
    renderAll();
}, {passive: false});

// Master Drag
let zMode = null, zStartX = 0, oZs = 0, oZe = 0;
zoomWindow.addEventListener('mousedown', e => {
    zStartX = e.clientX; oZs = zoomStartMs; oZe = zoomEndMs;
    if(e.target.classList.contains('handle-left')) zMode = 'left'; else if(e.target.classList.contains('handle-right')) zMode = 'right'; else zMode = 'pan';
    const mw = masterCanvas.clientWidth;
    const zMove = me => {
        const dxMs = ((me.clientX - zStartX) / mw) * totalTimeMs;
        if(zMode === 'pan') { const d = oZe - oZs; zoomStartMs = Math.max(0, Math.min(totalTimeMs - d, oZs + dxMs)); zoomEndMs = zoomStartMs + d; } 
        else if (zMode === 'right') zoomEndMs = Math.min(totalTimeMs, Math.max(zoomStartMs + 1000, oZe + dxMs));
        else if (zMode === 'left') zoomStartMs = Math.max(0, Math.min(zoomEndMs - 1000, oZs + dxMs));
        renderAll();
    };
    const zUp = () => { window.removeEventListener('mousemove', zMove); window.removeEventListener('mouseup', zUp); };
    window.addEventListener('mousemove', zMove); window.addEventListener('mouseup', zUp);
});

// ---- KEYBOARD SHORTCUTS ----
window.addEventListener('keydown', e => {
    if(e.target.tagName === 'INPUT') return;
    if ((e.ctrlKey && e.key.toLowerCase() === 'z') || e.key === ',') { undo(); e.preventDefault(); return; }
    if ((e.ctrlKey && e.key.toLowerCase() === 'y') || e.key === '.') { redo(); e.preventDefault(); return; }
    const map = {'f':'fire', 'a':'wind', 'l':'lightning', 'c':'color', 'm':'movieinfo'}; if(map[e.key.toLowerCase()]) selectTrack(map[e.key.toLowerCase()]);
    if((e.key === 'Delete' || e.key === 'Backspace') && selectedItemId) {
        dataPoints = dataPoints.filter(p => p.id !== selectedItemId); dataBlocks = dataBlocks.filter(b => b.id !== selectedItemId);
        selectedItemId = null; saveState(); renderAll(); hideContextMenu();
    }
    if (e.ctrlKey && e.key.toLowerCase() === 'm') { e.preventDefault(); toggleMute(); }
    
    const dur = zoomEndMs - zoomStartMs;
    if (e.key === 'ArrowRight') {
        if(e.shiftKey) { zoomStartMs = Math.min(totalTimeMs - dur, zoomStartMs + (dur*0.1)); zoomEndMs = zoomStartMs + dur; } 
        else { playheadMs = Math.min(totalTimeMs, snapMs(playheadMs + frameMs)); } renderAll(); e.preventDefault();
    } else if (e.key === 'ArrowLeft') {
        if(e.shiftKey) { zoomStartMs = Math.max(0, zoomStartMs - (dur*0.1)); zoomEndMs = zoomStartMs + dur; } 
        else { playheadMs = Math.max(0, snapMs(playheadMs - frameMs)); } renderAll(); e.preventDefault();
    } else if (e.key === 'ArrowUp') {
        zoomStartMs = Math.max(0, zoomStartMs - dur); zoomEndMs = zoomStartMs + dur; renderAll(); e.preventDefault();
    } else if (e.key === 'ArrowDown') {
        zoomStartMs = Math.min(totalTimeMs - dur, zoomStartMs + dur); zoomEndMs = zoomStartMs + dur; renderAll(); e.preventDefault();
    }
    
    const numMap = {'1':10, '2':20, '3':30, '4':40, '5':50, '6':60, '7':70, '8':80, '9':90, '0':100, '.':0, '-':0};
    if(numMap[e.key] !== undefined && selectedItemId) {
        const pt = dataPoints.find(p => p.id === selectedItemId);
        if(pt) { pt.val = snapIntensity(pt.trackId, numMap[e.key]); saveState(); renderAll(); }
    }
});

function toggleMute() {
    isMuted = !isMuted;
    if(isMuted) { lastVolume = volumeSlider.value; volumeSlider.value = 0; btnMute.innerHTML = '<i class="fas fa-volume-mute"></i>'; } 
    else { volumeSlider.value = lastVolume; btnMute.innerHTML = '<i class="fas fa-volume-up"></i>'; }
}
btnMute.addEventListener('click', toggleMute);
volumeSlider.addEventListener('input', () => { if(volumeSlider.value > 0 && isMuted) { isMuted = false; btnMute.innerHTML = '<i class="fas fa-volume-up"></i>'; } });

btnTrash.addEventListener('click', () => {
    if(selectedItemId) { dataPoints = dataPoints.filter(p => p.id !== selectedItemId); selectedItemId = null; saveState(); renderAll(); hideContextMenu(); }
});
document.getElementById('btn-undo').addEventListener('click', undo);
document.getElementById('btn-redo').addEventListener('click', redo);

// Modals
document.getElementById('menu-settings').onclick = () => { document.getElementById('modal-overlay').style.display = 'block'; document.getElementById('modal-settings').style.display = 'block'; };
document.getElementById('menu-shortcuts').onclick = () => { document.getElementById('modal-overlay').style.display = 'block'; document.getElementById('modal-shortcuts').style.display = 'block'; };
document.querySelectorAll('.btn-close-modal').forEach(btn => {
    btn.onclick = () => {
        document.getElementById('modal-overlay').style.display = 'none'; document.querySelectorAll('.modal').forEach(m => m.style.display = 'none');
        settings.minDistMs = document.getElementById('setting-min-dist').value;
        if (selectedTrackId) updateContextTools(tracksDef.find(t => t.id === selectedTrackId));
    };
});

// Skip buttons integration
document.getElementById('btn-skip-frame-forward').onclick = () => { playheadMs = snapMs(playheadMs + frameMs); renderAll(); };
document.getElementById('btn-skip-frame-back').onclick = () => { playheadMs = Math.max(0, snapMs(playheadMs - frameMs)); renderAll(); };
document.getElementById('btn-skip-1s-forward').onclick = () => { playheadMs = snapMs(playheadMs + 1000); renderAll(); };
document.getElementById('btn-skip-1s-back').onclick = () => { playheadMs = Math.max(0, snapMs(playheadMs - 1000)); renderAll(); };
document.getElementById('btn-skip-10s-forward').onclick = () => { playheadMs = snapMs(playheadMs + 10000); renderAll(); };
document.getElementById('btn-skip-10s-back').onclick = () => { playheadMs = Math.max(0, snapMs(playheadMs - 10000)); renderAll(); };
document.getElementById('btn-skip-1m-forward').onclick = () => { playheadMs = snapMs(playheadMs + 60000); renderAll(); };
document.getElementById('btn-skip-1m-back').onclick = () => { playheadMs = Math.max(0, snapMs(playheadMs - 60000)); renderAll(); };

// Init
window.addEventListener('resize', renderAll);
renderAll();
