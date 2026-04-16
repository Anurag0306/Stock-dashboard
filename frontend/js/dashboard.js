const API = 'http://localhost:8000';
const WS  = 'ws://localhost:8000/ws';

// ── State ─────────────────────────────────────────────────────────────────
let allPrices   = [];
let allNews     = [];
let currentPage = 'overview';
let ws          = null;
let moodHistory = [];
let newsFilter  = 'all';

// ── Clock ─────────────────────────────────────────────────────────────────
function updateClock() {
  document.getElementById('clock').textContent =
    new Date().toLocaleTimeString('en-IN', { timeZone:'Asia/Kolkata' }) + ' IST';
}
setInterval(updateClock, 1000);
updateClock();

// ── Sidebar ───────────────────────────────────────────────────────────────
function toggleSidebar() {
  document.getElementById('sidebar').classList.toggle('collapsed');
}

// ── Navigation ────────────────────────────────────────────────────────────
function navigateTo(page) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.getElementById(`page-${page}`)?.classList.add('active');
  document.querySelector(`[data-page="${page}"]`)?.classList.add('active');
  currentPage = page;

  if (page === 'india')       renderIndiaPage();
  if (page === 'portfolio') loadPortfolio();
  if (page === 'global')      renderGlobalPage();
  if (page === 'commodities') renderDetailPage('commodity-cards-full','commodity','commodity-detail');
  if (page === 'forex')       renderDetailPage('forex-cards-full','forex','forex-detail');
  if (page === 'crypto')      renderDetailPage('crypto-cards-full','crypto','crypto-detail');
  if (page === 'mood')        renderMoodPage();
  if (page === 'sentiment')   renderSentimentPage();
  if (page === 'heatmap')     loadHeatmap();
  if (page === 'impact')      renderImpactPage();
  if (page === 'news')        renderNewsPage();
  if (page === 'economic')    renderEconomicPage();
  if (page === 'calendar')    renderCalendar();
  if (page === 'aibrief') {
  // Auto-load sentiment on page open
    loadAISentiment();
  }
  if (page === 'probability') loadProbabilityData();
  if (page === 'screener') loadScreener();
  if (page === 'watchlist') loadWatchlist();
  if (page === 'quant') loadQuantData();
  if (page === 'technical') {
  loadTechnicalScan();
  loadTechnicalDetail('^NSEI', null);
}
}

// ── WebSocket ─────────────────────────────────────────────────────────────
function connectWS() {
  ws = new WebSocket(WS);
  ws.onopen = () => {
    document.getElementById('ws-dot').classList.add('live');
    document.getElementById('ws-status').textContent = 'Live';
  };
  ws.onmessage = e => {
    const msg = JSON.parse(e.data);
    if (msg.type === 'prices') { allPrices = msg.data; renderAll(); }
  };
  ws.onclose = () => {
    document.getElementById('ws-dot').classList.remove('live');
    document.getElementById('ws-status').textContent = 'Reconnecting...';
    setTimeout(connectWS, 5000);
  };
  ws.onerror = () => ws.close();
}

// ── Format helpers ────────────────────────────────────────────────────────
function fmt(price, type) {
  if (!price && price !== 0) return '--';
  if (type === 'crypto') return '$' + Number(price).toLocaleString('en-US', {maximumFractionDigits:2});
  if (type === 'forex')  return Number(price).toFixed(4);
  if (type === 'bond')   return Number(price).toFixed(3) + '%';
  return Number(price).toLocaleString('en-IN', {maximumFractionDigits:2});
}
function chgClass(c) { return !c ? 'flat' : c > 0 ? 'up' : 'down'; }
function chgArrow(c) { return !c ? '▸' : c > 0 ? '▲' : '▼'; }
function chgStr(c)   { if(!c) return '0.00%'; return `${c>=0?'+':''}${Number(c).toFixed(2)}%`; }

// ── Ticker ────────────────────────────────────────────────────────────────
function updateTicker(prices) {
  const items = prices.slice(0,20).map(p => {
    const c   = p.change_pct || 0;
    const col = c > 0 ? '#00c896' : c < 0 ? '#ff4560' : '#8899bb';
    return `<span style="margin:0 20px;color:${col}">
      ${p.asset_name} &nbsp;
      <strong>${fmt(p.price, p.asset_type)}</strong>
      &nbsp; ${chgArrow(c)} ${chgStr(c)}
    </span>`;
  });
  document.getElementById('ticker').innerHTML =
    `<span class="ticker-inner">${items.join('')}</span>`;
}

// ── KPI Row ───────────────────────────────────────────────────────────────
const KPI_ASSETS = ['NIFTY 50','Sensex','S&P 500','NASDAQ','Gold','Crude Oil WTI','Bitcoin','USD/INR'];

function renderKPIRow(prices) {
  const el = document.getElementById('kpi-row');
  if (!el) return;
  const map = Object.fromEntries(prices.map(p => [p.asset_name, p]));
  el.innerHTML = KPI_ASSETS.map(name => {
    const p = map[name];
    if (!p) return '';
    const c = p.change_pct || 0;
    return `<div class="kpi-card">
      <div class="kpi-name">${name}</div>
      <div class="kpi-price">${fmt(p.price, p.asset_type)}</div>
      <div class="kpi-change ${chgClass(c)}">${chgArrow(c)} ${chgStr(c)}</div>
    </div>`;
  }).join('');
}

// ── Asset Table ───────────────────────────────────────────────────────────
function renderTable(containerId, prices) {
  const el = document.getElementById(containerId);
  if (!el || !prices.length) return;
  el.innerHTML = prices.map(p => {
    const c = p.change_pct || 0;
    return `<div class="asset-row">
      <div class="asset-row-name">${p.asset_name}</div>
      <div class="asset-row-price">${fmt(p.price, p.asset_type)}</div>
      <div class="asset-row-chg ${chgClass(c)}">${chgArrow(c)} ${chgStr(c)}</div>
    </div>`;
  }).join('');
}

// ── Big Cards ─────────────────────────────────────────────────────────────
function renderBigCards(containerId, prices) {
  const el = document.getElementById(containerId);
  if (!el) return;
  el.innerHTML = prices.map(p => {
    const c = p.change_pct || 0;
    return `<div class="big-card ${chgClass(c)}">
      <div class="big-card-name">${p.asset_name}</div>
      <div class="big-card-price">${fmt(p.price, p.asset_type)}</div>
      <div class="big-card-chg ${chgClass(c)}">${chgArrow(c)} ${chgStr(c)}</div>
    </div>`;
  }).join('');
}

// ── Gainers / Losers table ────────────────────────────────────────────────
function renderGainersLosers(gainerId, loserId, prices) {
  const sorted = [...prices].filter(p => p.change_pct != null)
    .sort((a,b) => b.change_pct - a.change_pct);
  const gainers = sorted.filter(p => p.change_pct > 0).slice(0,5);
  const losers  = sorted.filter(p => p.change_pct < 0).reverse().slice(0,5);

  const makeRow = p => {
    const c = p.change_pct || 0;
    return `<div class="asset-row">
      <div class="asset-row-name">${p.asset_name}</div>
      <div class="asset-row-price">${fmt(p.price, p.asset_type)}</div>
      <div class="asset-row-chg ${chgClass(c)}">${chgArrow(c)} ${chgStr(c)}</div>
    </div>`;
  };

  const gEl = document.getElementById(gainerId);
  const lEl = document.getElementById(loserId);
  if (gEl) gEl.innerHTML = gainers.length ? gainers.map(makeRow).join('') : '<div style="padding:16px;color:var(--text-dim)">No gainers today</div>';
  if (lEl) lEl.innerHTML = losers.length  ? losers.map(makeRow).join('')  : '<div style="padding:16px;color:var(--text-dim)">No losers today</div>';
}

// ── Detail Table (with extra info) ────────────────────────────────────────
function renderDetailTable(containerId, prices) {
  const el = document.getElementById(containerId);
  if (!el || !prices.length) return;
  el.innerHTML = `
    <table style="width:100%;border-collapse:collapse">
      <thead>
        <tr style="border-bottom:1px solid var(--border)">
          <th style="padding:10px 16px;text-align:left;color:var(--text-dim);font-size:0.75rem;font-weight:600">ASSET</th>
          <th style="padding:10px 16px;text-align:right;color:var(--text-dim);font-size:0.75rem;font-weight:600">PRICE</th>
          <th style="padding:10px 16px;text-align:right;color:var(--text-dim);font-size:0.75rem;font-weight:600">CHANGE</th>
          <th style="padding:10px 16px;text-align:right;color:var(--text-dim);font-size:0.75rem;font-weight:600">SIGNAL</th>
        </tr>
      </thead>
      <tbody>
        ${prices.map(p => {
          const c   = p.change_pct || 0;
          const sig = c > 2 ? '🔥 Strong Buy' : c > 0.5 ? '📈 Bullish' :
                      c < -2 ? '🚨 Strong Sell' : c < -0.5 ? '📉 Bearish' : '➡️ Neutral';
          const sigCol = c > 0.5 ? 'var(--green)' : c < -0.5 ? 'var(--red)' : 'var(--text-dim)';
          return `<tr style="border-bottom:1px solid var(--border);transition:background 0.15s"
            onmouseover="this.style.background='var(--bg-hover)'"
            onmouseout="this.style.background=''">
            <td style="padding:11px 16px;color:var(--text-pri);font-weight:500">${p.asset_name}</td>
            <td style="padding:11px 16px;text-align:right;font-family:monospace;color:var(--text-pri)">${fmt(p.price, p.asset_type)}</td>
            <td style="padding:11px 16px;text-align:right;font-family:monospace;font-weight:600;color:${c>0?'var(--green)':c<0?'var(--red)':'var(--text-dim)'}">${chgArrow(c)} ${chgStr(c)}</td>
            <td style="padding:11px 16px;text-align:right;font-size:0.8rem;color:${sigCol}">${sig}</td>
          </tr>`;
        }).join('')}
      </tbody>
    </table>`;
}

// ── India Page ────────────────────────────────────────────────────────────
function renderIndiaPage() {
  const prices = allPrices.filter(p => p.asset_type === 'indian_index');
  renderBigCards('india-cards-full', prices);
  renderGainersLosers('india-gainers', 'india-losers', allPrices);
}

// ── Global Page ───────────────────────────────────────────────────────────
function renderGlobalPage() {
  const prices = allPrices.filter(p => p.asset_type === 'global_index');
  renderBigCards('global-cards-full', prices);
  renderGainersLosers('global-gainers', 'global-losers', allPrices);
}

// ── Detail Page (commodities / forex / crypto) ────────────────────────────
function renderDetailPage(cardsId, assetType, detailId) {
  const prices = allPrices.filter(p => p.asset_type === assetType);
  renderBigCards(cardsId, prices);
  renderDetailTable(detailId, prices);
}

// ── Market Mood ───────────────────────────────────────────────────────────
function computeMood(prices) {
  const map = Object.fromEntries(prices.map(p => [p.asset_name, p]));
  const components = [];
  let total = 0, count = 0;

  const defs = [
    { name:'NIFTY 50',      label:'NIFTY Momentum',   invert:false },
    { name:'S&P 500',       label:'S&P Momentum',     invert:false },
    { name:'Gold',          label:'Gold (Risk-Off)',   invert:true  },
    { name:'US 10Y Yield',  label:'Bond Yields',      invert:true  },
    { name:'Bitcoin',       label:'Crypto Sentiment', invert:false },
    { name:'Dollar Index',  label:'Dollar Strength',  invert:true  },
    { name:'Crude Oil WTI', label:'Crude Oil',        invert:false },
    { name:'USD/INR',       label:'Rupee Strength',   invert:true  },
  ];

  defs.forEach(d => {
    const p = map[d.name];
    if (!p) return;
    const c   = p.change_pct || 0;
    let raw   = Math.min(Math.max(c * 10 + 50, 0), 100);
    if (d.invert) raw = 100 - raw;
    components.push({ label:d.label, value:Math.round(raw) });
    total += raw; count++;
  });

  const mood = count ? Math.round(total / count) : 50;
  let tag, regime;
  if      (mood >= 80) { tag = '🤑 Extreme Greed'; regime = 'RISK-ON';  }
  else if (mood >= 60) { tag = '😊 Greed';          regime = 'BULLISH';  }
  else if (mood >= 45) { tag = '😐 Neutral';         regime = 'MIXED';    }
  else if (mood >= 25) { tag = '😟 Fear';            regime = 'RISK-OFF'; }
  else                 { tag = '😨 Extreme Fear';    regime = 'CRISIS';   }

  return { mood, tag, regime, components };
}

function renderMoodBanner(prices) {
  const { mood, tag, regime, components } = computeMood(prices);
  const scoreEl  = document.getElementById('mood-score-banner');
  const tagEl    = document.getElementById('mood-tag-banner');
  const needleEl = document.getElementById('mood-needle');
  const regimeEl = document.getElementById('regime-badge');
  if (scoreEl)  { scoreEl.textContent  = mood; scoreEl.style.color = mood>=60?'#00c896':mood>=45?'#ffb800':'#ff4560'; }
  if (tagEl)    tagEl.textContent    = tag;
  if (needleEl) needleEl.style.left  = mood + '%';
  if (regimeEl) regimeEl.textContent = regime;
  moodHistory.push({ time: new Date().toLocaleTimeString(), mood });
  if (moodHistory.length > 50) moodHistory.shift();
  return { mood, tag, regime, components };
}

function renderMoodPage() {
  const { mood, tag, regime, components } = computeMood(allPrices);

  // Gauge
  const canvas = document.getElementById('gauge-chart');
  if (canvas) {
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const cx = 170, cy = 160, r = 120;
    ctx.beginPath();
    ctx.arc(cx, cy, r, Math.PI, 2*Math.PI);
    const grad = ctx.createLinearGradient(50, 0, 290, 0);
    grad.addColorStop(0,   '#d32f2f');
    grad.addColorStop(0.3, '#ff9800');
    grad.addColorStop(0.5, '#ffeb3b');
    grad.addColorStop(0.7, '#8bc34a');
    grad.addColorStop(1,   '#1b5e20');
    ctx.strokeStyle = grad;
    ctx.lineWidth   = 20;
    ctx.stroke();
    const angle = Math.PI + (mood / 100) * Math.PI;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(cx + Math.cos(angle)*100, cy + Math.sin(angle)*100);
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth   = 3;
    ctx.stroke();
    ctx.beginPath();
    ctx.arc(cx, cy, 8, 0, 2*Math.PI);
    ctx.fillStyle = '#ffffff';
    ctx.fill();
    const scoreEl = document.getElementById('gauge-score');
    const labelEl = document.getElementById('gauge-label');
    if (scoreEl) scoreEl.textContent = mood;
    if (labelEl) labelEl.textContent = tag;
  }

  // Components
  const compEl = document.getElementById('mood-components');
  if (compEl) {
    compEl.innerHTML = components.map(c => {
      const col = c.value>=60?'#00c896':c.value>=40?'#ffb800':'#ff4560';
      return `<div class="mood-component">
        <div class="mc-name">${c.label}</div>
        <div class="mc-bar-wrap">
          <div class="mc-bar" style="width:${c.value}%;background:${col}"></div>
        </div>
        <div class="mc-value" style="color:${col}">${c.value}</div>
      </div>`;
    }).join('');
  }

  // Regime
  const regEl = document.getElementById('regime-detail');
  if (regEl) {
    const regimes = {
      'RISK-ON': { desc:'Strong bullish momentum. FII inflows likely, equities favored.', color:'#00c896' },
      'BULLISH': { desc:'Positive sentiment. Markets trending up with moderate risk appetite.', color:'#8bc34a' },
      'MIXED':   { desc:'Mixed signals. Market consolidating — watch key levels.', color:'#ffb800' },
      'RISK-OFF':{ desc:'Fear in markets. Investors moving to bonds, gold, USD.', color:'#ff9800' },
      'CRISIS':  { desc:'Extreme fear. Sharp corrections likely. Watch FII outflows.', color:'#ff4560' },
    };
    const r = regimes[regime] || regimes['MIXED'];
    regEl.innerHTML = `
      <div style="padding:24px;text-align:center">
        <div style="font-size:2rem;font-weight:800;color:${r.color};margin-bottom:12px">${regime}</div>
        <div style="font-size:0.9rem;color:var(--text-sec);line-height:1.7;max-width:280px;margin:0 auto">${r.desc}</div>
      </div>
      <div style="padding:0 8px 16px">
        ${allPrices.slice(0,6).map(p => {
          const c = p.change_pct || 0;
          return `<div class="asset-row">
            <div class="asset-row-name">${p.asset_name}</div>
            <div class="asset-row-price">${fmt(p.price, p.asset_type)}</div>
            <div class="asset-row-chg ${chgClass(c)}">${chgArrow(c)} ${chgStr(c)}</div>
          </div>`;
        }).join('')}
      </div>`;
  }

  // History chart
  if (moodHistory.length > 1) {
    const ctx2 = document.getElementById('mood-history-chart')?.getContext('2d');
    if (ctx2) {
      if (window._moodChart) window._moodChart.destroy();
      window._moodChart = new Chart(ctx2, {
        type: 'line',
        data: {
          labels: moodHistory.map(m => m.time),
          datasets: [{
            data: moodHistory.map(m => m.mood),
            borderColor: '#1e90ff',
            backgroundColor: 'rgba(30,144,255,0.08)',
            tension: 0.4, fill: true, pointRadius: 2,
          }]
        },
        options: {
          plugins: { legend:{ display:false } },
          scales: {
            y: { min:0, max:100, grid:{ color:'#1a2540' }, ticks:{ color:'#8899bb' } },
            x: { grid:{ color:'#1a2540' }, ticks:{ color:'#8899bb', maxTicksLimit:8 } }
          }
        }
      });
    }
  }
}

// ── Sentiment ─────────────────────────────────────────────────────────────
const BULLISH_WORDS = ['surge','rally','gain','rise','bull','high','growth','up','positive','strong','record','soar','jump'];
const BEARISH_WORDS = ['fall','drop','crash','decline','bear','low','loss','down','negative','weak','sell','fear','plunge'];

function scoreSentiment(title) {
  const t = title.toLowerCase();
  let s = 0;
  BULLISH_WORDS.forEach(w => { if(t.includes(w)) s++; });
  BEARISH_WORDS.forEach(w => { if(t.includes(w)) s--; });
  return s;
}

function renderSentimentPage() {
  const scored = allNews.map(n => ({ ...n, score: scoreSentiment(n.title) }));
  const total  = scored.length || 1;
  const bull   = scored.filter(n => n.score > 0).length;
  const bear   = scored.filter(n => n.score < 0).length;
  const neut   = scored.filter(n => n.score === 0).length;

  const summEl = document.getElementById('sentiment-summary');
  if (summEl) {
    summEl.innerHTML = `
      <div class="sentiment-card">
        <div class="s-pct bullish">${Math.round(bull/total*100)}%</div>
        <div class="s-label">😊 Bullish Headlines</div>
      </div>
      <div class="sentiment-card">
        <div class="s-pct neutral-col">${Math.round(neut/total*100)}%</div>
        <div class="s-label">😐 Neutral Headlines</div>
      </div>
      <div class="sentiment-card">
        <div class="s-pct bearish">${Math.round(bear/total*100)}%</div>
        <div class="s-label">😟 Bearish Headlines</div>
      </div>`;
  }

  const listEl = document.getElementById('sentiment-news-list');
  if (listEl) {
    const sorted = [...scored].sort((a,b) => Math.abs(b.score)-Math.abs(a.score));
    listEl.innerHTML = sorted.slice(0,40).map(n => {
      const cls = n.score>0?'pos':n.score<0?'neg':'neu';
      const lbl = n.score>0?'📈 Bullish':n.score<0?'📉 Bearish':'➡️ Neutral';
      return `<div class="sentiment-news-item">
        <div class="sni-title">${n.title}</div>
        <span class="sni-score ${cls}">${lbl}</span>
      </div>`;
    }).join('');
  }
}

// ── Heatmap ───────────────────────────────────────────────────────────────
async function loadHeatmap() {
  const container = document.getElementById('heatmap-container');
  if (!container) return;
  try {
    const res  = await fetch(`${API}/api/correlation`);
    const json = await res.json();
    const data = json.data;
    if (!data || Object.keys(data).length < 3) {
      buildEstimatedHeatmap(container);
      return;
    }
    renderHeatmapTable(container, data);
  } catch(e) {
    buildEstimatedHeatmap(container);
  }
}

function buildEstimatedHeatmap(container) {
  const prices = allPrices.slice(0,14);
  if (!prices.length) { container.innerHTML = '<p style="padding:20px;color:var(--text-dim)">No data yet.</p>'; return; }
  const matrix = {};
  prices.forEach(a => {
    matrix[a.asset_name] = {};
    prices.forEach(b => {
      if (a.asset_name === b.asset_name) { matrix[a.asset_name][b.asset_name] = 1.0; return; }
      const ca = a.change_pct||0, cb = b.change_pct||0;
      const same = (ca>=0)===(cb>=0);
      const str  = Math.min(Math.abs(ca*cb)/10, 0.9);
      matrix[a.asset_name][b.asset_name] = same ? str : -str;
    });
  });
  container.innerHTML = '<p style="color:var(--yellow);font-size:0.78rem;padding:0 0 10px">⏳ Estimated — full statistical heatmap builds after ~1hr</p>';
  renderHeatmapTable(container, matrix);
}

function renderHeatmapTable(container, data) {
  const labels = Object.keys(data);
  const short  = l => l.length>12 ? l.slice(0,12)+'…' : l;
  function cellStyle(v) {
    if (v >= 0.8)  return ['rgba(0,200,150,0.9)',  '#fff'];
    if (v >= 0.5)  return ['rgba(0,200,150,0.55)', '#fff'];
    if (v >= 0.2)  return ['rgba(0,200,150,0.25)', '#ccc'];
    if (v >= -0.2) return ['rgba(136,153,187,0.1)','#888'];
    if (v >= -0.5) return ['rgba(255,69,96,0.25)', '#ccc'];
    if (v >= -0.8) return ['rgba(255,69,96,0.55)', '#fff'];
    return              ['rgba(255,69,96,0.9)',  '#fff'];
  }
  const html = `
    <div style="overflow-x:auto">
    <table style="border-collapse:collapse;font-size:0.72rem">
      <tr>
        <th style="padding:6px 10px;color:var(--accent);text-align:left;min-width:120px">Asset</th>
        ${labels.map(l=>`<th style="padding:4px 6px;color:var(--text-dim);text-align:center;
          writing-mode:vertical-lr;transform:rotate(180deg);height:80px;white-space:nowrap">
          ${short(l)}</th>`).join('')}
      </tr>
      ${labels.map(a=>`
        <tr>
          <td style="padding:6px 10px;color:var(--text-pri);font-weight:600;
            border-right:1px solid var(--border);white-space:nowrap">${short(a)}</td>
          ${labels.map(b=>{
            const v = (data[a]&&data[a][b]!==undefined)?data[a][b]:0;
            const [bg,col] = cellStyle(v);
            return `<td title="${a} ↔ ${b}: ${Number(v).toFixed(4)}"
              style="padding:5px 4px;text-align:center;background:${bg};color:${col};
              border:1px solid #070b14;min-width:48px;border-radius:2px;cursor:default">
              ${Number(v).toFixed(2)}</td>`;
          }).join('')}
        </tr>`).join('')}
    </table></div>
    <div style="display:flex;gap:16px;margin-top:12px;font-size:0.75rem;color:var(--text-dim);flex-wrap:wrap;padding:4px">
      <span style="color:var(--green)">■ Strong positive</span>
      <span>■ Neutral</span>
      <span style="color:var(--red)">■ Negative</span>
    </div>`;
  container.innerHTML = html;
}

// ── Impact ────────────────────────────────────────────────────────────────
async function renderImpactPage() {
  try {
    const [impRes, ruleRes] = await Promise.all([
      fetch(`${API}/api/impact`),
      fetch(`${API}/api/rules`)
    ]);
    const impJson  = await impRes.json();
    const ruleJson = await ruleRes.json();

    const impEl = document.getElementById('impact-full');
    if (impEl) {
      impEl.innerHTML = !impJson.triggered.length
        ? '<div class="no-alerts">✅ No major alerts — markets are calm.</div>'
        : impJson.triggered.map(i=>`
            <div class="impact-card ${i.severity}">
              <div class="impact-title">${i.direction} ${i.trigger} &nbsp; ${i.change>=0?'+':''}${i.change}%</div>
              <div class="impact-body">${i.insight}</div>
              <div class="impact-affects">Affects: ${i.affects.join(', ')}</div>
            </div>`).join('');
    }

    const rulesEl = document.getElementById('rules-list');
    if (rulesEl && ruleJson.data) {
      rulesEl.innerHTML = ruleJson.data.map(r=>`
        <div class="rule-card">
          <div class="rule-trigger">📌 ${r.trigger}</div>
          <div class="rule-insight">${r.insight.slice(0,120)}...</div>
          <div class="rule-threshold">±${r.threshold}%</div>
        </div>`).join('');
    }
  } catch(e) { console.error('Impact error:', e); }
}

async function renderImpactOverview() {
  try {
    const res  = await fetch(`${API}/api/impact`);
    const json = await res.json();
    const el   = document.getElementById('impact-overview');
    if (!el) return;
    el.innerHTML = !json.triggered.length
      ? '<div class="no-alerts" style="padding:16px">✅ Markets calm — no active alerts.</div>'
      : json.triggered.slice(0,3).map(i=>`
          <div class="impact-card ${i.severity}">
            <div class="impact-title">${i.direction} ${i.trigger} ${i.change>=0?'+':''}${i.change}%</div>
            <div class="impact-body">${i.insight.slice(0,120)}...</div>
          </div>`).join('');
  } catch(e) {}
}

// ── News ──────────────────────────────────────────────────────────────────
function renderNewsPage() {
  const filtered = newsFilter==='all' ? allNews : allNews.filter(n=>n.category===newsFilter);
  const el = document.getElementById('news-full-list');
  if (!el) return;
  el.innerHTML = filtered.slice(0,60).map(n=>`
    <div class="news-card">
      <div>
        <span class="news-badge badge-${n.category}">${n.category.toUpperCase()}</span><br/>
        <a href="${n.url}" target="_blank">${n.title}</a>
      </div>
      <div class="news-meta">
        <div class="news-source">${n.source}</div>
        <div style="font-size:0.7rem;color:var(--text-dim);margin-top:2px">
          ${n.published ? new Date(n.published).toLocaleDateString('en-IN') : ''}
        </div>
      </div>
    </div>`).join('');
}

function filterNews(cat, btn) {
  newsFilter = cat;
  document.querySelectorAll('.filter-btn').forEach(b=>b.classList.remove('active'));
  if (btn) btn.classList.add('active');
  renderNewsPage();
}

function renderNewsOverview() {
  const el = document.getElementById('news-overview');
  if (!el) return;
  el.innerHTML = allNews.slice(0,6).map(n=>`
    <div style="padding:10px 16px;border-bottom:1px solid var(--border)">
      <span class="news-badge badge-${n.category}">${n.category.toUpperCase()}</span>
      <div style="margin-top:4px">
        <a href="${n.url}" target="_blank"
          style="color:var(--text-pri);font-size:0.84rem;line-height:1.4;text-decoration:none">
          ${n.title}
        </a>
      </div>
      <div style="font-size:0.72rem;color:var(--text-dim);margin-top:3px">${n.source}</div>
    </div>`).join('');
}

// ── Economic ──────────────────────────────────────────────────────────────
async function renderEconomicPage() {
  try {
    const res  = await fetch(`${API}/api/economic`);
    const json = await res.json();
    const el   = document.getElementById('economic-cards');
    if (!el) return;
    el.innerHTML = json.data.map(e=>`
      <div class="eco-card">
        <div class="eco-name">${e.indicator}</div>
        <div class="eco-value">${Number(e.value).toLocaleString()}</div>
        <div class="eco-period">as of ${e.period||'latest'}</div>
      </div>`).join('');
  } catch(e) {}
}

// ── Calendar ──────────────────────────────────────────────────────────────
function renderCalendar() {
  const events = [
    { date:'Apr 09, 2026', title:'US CPI Inflation Release',        importance:'high'   },
    { date:'Apr 10, 2026', title:'US PPI Data Release',             importance:'medium' },
    { date:'Apr 15, 2026', title:'US Retail Sales',                 importance:'high'   },
    { date:'Apr 16, 2026', title:'Fed Beige Book Release',          importance:'medium' },
    { date:'Apr 17, 2026', title:'ECB Interest Rate Decision',      importance:'high'   },
    { date:'Apr 22, 2026', title:'RBI Monetary Policy Meeting',     importance:'high'   },
    { date:'Apr 24, 2026', title:'India GDP Q3 Release',            importance:'high'   },
    { date:'Apr 25, 2026', title:'US GDP Advance Estimate',         importance:'high'   },
    { date:'Apr 29, 2026', title:'India GST Collection Data',       importance:'medium' },
    { date:'Apr 30, 2026', title:'FOMC Meeting & Rate Decision',    importance:'high'   },
    { date:'May 05, 2026', title:'RBI Repo Rate Decision',          importance:'high'   },
    { date:'May 09, 2026', title:'India IIP Data Release',          importance:'medium' },
    { date:'May 13, 2026', title:'US CPI Inflation (April)',        importance:'high'   },
    { date:'May 15, 2026', title:'India WPI Release',               importance:'medium' },
  ];
  const el = document.getElementById('calendar-list');
  if (!el) return;
  el.innerHTML = events.map(e=>`
    <div class="cal-event">
      <div class="cal-date">📅 ${e.date}</div>
      <div class="cal-title">${e.title}</div>
      <div class="cal-imp ${e.importance}">${e.importance.toUpperCase()}</div>
    </div>`).join('');
}

// ── Render All ────────────────────────────────────────────────────────────
function renderAll() {
  updateTicker(allPrices);
  renderKPIRow(allPrices);
  renderMoodBanner(allPrices);
  renderTable('india-table',  allPrices.filter(p=>p.asset_type==='indian_index'));
  renderTable('global-table', allPrices.filter(p=>p.asset_type==='global_index'));
  renderTable('commodity-table-overview', allPrices.filter(p=>p.asset_type==='commodity'));
  renderTable('forex-table-overview',     allPrices.filter(p=>p.asset_type==='forex'));
  renderTable('crypto-table-overview',    allPrices.filter(p=>p.asset_type==='crypto'));
  const now = new Date().toLocaleTimeString('en-IN',{timeZone:'Asia/Kolkata'});
  ['india-update','global-update'].forEach(id=>{
    const el = document.getElementById(id);
    if (el) el.textContent = `Updated ${now}`;
  });
  if (currentPage !== 'overview') navigateTo(currentPage);
}

// ── Init ──────────────────────────────────────────────────────────────────
async function init() {
  updateClock();
  try {
    const res  = await fetch(`${API}/api/summary`);
    const json = await res.json();
    allPrices  = json.prices || [];
    allNews    = json.news   || [];
    renderAll();
    renderNewsOverview();
    renderImpactOverview();
  } catch(e) {
    console.error('Init failed:', e);
    document.getElementById('ws-status').textContent = 'API Offline';
  }
  connectWS();
  setInterval(async () => {
    try {
      const res  = await fetch(`${API}/api/summary`);
      const json = await res.json();
      allPrices  = json.prices || [];
      allNews    = json.news   || [];
      renderAll();
      renderNewsOverview();
      renderImpactOverview();
    } catch(e) {}
  }, 30000);
}
// ── Portfolio ─────────────────────────────────────────────────────────────
const ALLOC_COLORS = [
  '#1e90ff','#00c896','#ffb800','#ff4560',
  '#a78bfa','#f97316','#06b6d4','#84cc16'
];

async function loadPortfolio() {
  const summEl = document.getElementById('port-summary');
  if (summEl) {
    ['port-invested','port-value','port-pnl','port-pct'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.textContent = '⏳';
    });
  }

  try {
    const res  = await fetch(`${API}/api/portfolio`);
    const json = await res.json();
    renderPortfolioSummary(json.summary);
    renderHoldingsTable(json.holdings);
    renderAllocation(json.holdings);
    renderPerformers(json.holdings);
  } catch(e) {
    console.error('Portfolio error:', e);
  }
}

function renderPortfolioSummary(s) {
  if (!s || !s.total_invested) return;
  const pnlPos = s.total_pnl >= 0;

  const inv = document.getElementById('port-invested');
  const val = document.getElementById('port-value');
  const pnl = document.getElementById('port-pnl');
  const pct = document.getElementById('port-pct');

  if (inv) inv.textContent = '₹' + Number(s.total_invested).toLocaleString('en-IN', {maximumFractionDigits:0});
  if (val) { val.textContent = '₹' + Number(s.total_value).toLocaleString('en-IN', {maximumFractionDigits:0}); val.style.color = 'var(--accent2)'; }
  if (pnl) { pnl.textContent = (pnlPos?'▲ ₹':'▼ ₹') + Math.abs(s.total_pnl).toLocaleString('en-IN',{maximumFractionDigits:0}); pnl.style.color = pnlPos ? 'var(--green)' : 'var(--red)'; }
  if (pct) { pct.textContent = (pnlPos?'+':'') + s.total_pnl_pct.toFixed(2) + '%'; pct.style.color = pnlPos ? 'var(--green)' : 'var(--red)'; }
}

function renderHoldingsTable(holdings) {
  const el = document.getElementById('port-holdings');
  if (!el) return;

  if (!holdings || !holdings.length) {
    el.innerHTML = '<div style="padding:40px;text-align:center;color:var(--text-dim)">No holdings yet. Add your first stock above ☝️</div>';
    return;
  }

  el.innerHTML = `
    <table class="holdings-table">
      <thead>
        <tr>
          <th>Stock</th>
          <th>Qty</th>
          <th>Buy Price</th>
          <th>Live Price</th>
          <th>Invested</th>
          <th>Value</th>
          <th>P&L</th>
          <th>Return</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        ${holdings.map(h => {
          const pos = h.pnl >= 0;
          const pnlColor = pos ? 'var(--green)' : 'var(--red)';
          const arr = pos ? '▲' : '▼';
          return `<tr>
            <td>
              <div style="font-weight:600;color:var(--text-pri)">${h.name}</div>
              <div style="font-size:0.72rem;color:var(--text-dim)">${h.symbol}</div>
            </td>
            <td>${h.quantity}</td>
            <td>₹${Number(h.buy_price).toLocaleString('en-IN',{maximumFractionDigits:2})}</td>
            <td style="color:var(--accent2)">₹${Number(h.live_price).toLocaleString('en-IN',{maximumFractionDigits:2})}</td>
            <td>₹${Number(h.invested).toLocaleString('en-IN',{maximumFractionDigits:0})}</td>
            <td>₹${Number(h.value).toLocaleString('en-IN',{maximumFractionDigits:0})}</td>
            <td style="color:${pnlColor}">${arr} ₹${Math.abs(h.pnl).toLocaleString('en-IN',{maximumFractionDigits:0})}</td>
            <td style="color:${pnlColor};font-weight:700">${h.pnl_pct>=0?'+':''}${h.pnl_pct.toFixed(2)}%</td>
            <td>
              <button class="del-btn" onclick="removeHolding(${h.id})">🗑</button>
            </td>
          </tr>`;
        }).join('')}
      </tbody>
    </table>`;
}

function renderAllocation(holdings) {
  const el = document.getElementById('port-allocation');
  if (!el || !holdings?.length) return;

  const totalValue = holdings.reduce((s, h) => s + h.value, 0);
  const sorted = [...holdings].sort((a,b) => b.value - a.value);

  el.innerHTML = sorted.map((h, i) => {
    const pct = totalValue ? (h.value / totalValue * 100) : 0;
    const col = ALLOC_COLORS[i % ALLOC_COLORS.length];
    return `<div class="alloc-row">
      <div class="alloc-name">${h.name.length>14?h.name.slice(0,14)+'…':h.name}</div>
      <div class="alloc-bar-wrap">
        <div class="alloc-bar" style="width:${pct}%;background:${col}"></div>
      </div>
      <div class="alloc-pct">${pct.toFixed(1)}%</div>
    </div>`;
  }).join('');
}

function renderPerformers(holdings) {
  const el = document.getElementById('port-performers');
  if (!el || !holdings?.length) return;

  const sorted = [...holdings].sort((a,b) => b.pnl_pct - a.pnl_pct);
  const best   = sorted.slice(0, 3);
  const worst  = sorted.slice(-3).reverse();

  const makeRow = (h, type) => {
    const col = type === 'best' ? 'var(--green)' : 'var(--red)';
    const arr = type === 'best' ? '▲' : '▼';
    return `<div class="asset-row">
      <div class="asset-row-name">${h.name}</div>
      <div class="asset-row-price" style="color:${col}">
        ${arr} ${Math.abs(h.pnl_pct).toFixed(2)}%
      </div>
    </div>`;
  };

  el.innerHTML = `
    <div style="padding:8px 16px;font-size:0.72rem;color:var(--green);font-weight:700;letter-spacing:0.5px">🏆 TOP GAINERS</div>
    ${best.map(h => makeRow(h,'best')).join('')}
    <div style="padding:8px 16px;font-size:0.72rem;color:var(--red);font-weight:700;letter-spacing:0.5px;margin-top:8px">📉 TOP LOSERS</div>
    ${worst.map(h => makeRow(h,'worst')).join('')}`;
}

async function addHolding() {
  const symbol = document.getElementById('port-symbol')?.value?.trim();
  const name   = document.getElementById('port-name')?.value?.trim();
  const qty    = parseFloat(document.getElementById('port-qty')?.value);
  const price  = parseFloat(document.getElementById('port-price')?.value);
  const type   = document.getElementById('port-type')?.value;

  if (!symbol || !name || !qty || !price) {
    alert('Please fill in all fields!');
    return;
  }

  try {
    const res = await fetch(`${API}/api/portfolio`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        symbol, name, quantity: qty,
        buy_price: price, asset_type: type
      })
    });

    if (res.ok) {
      // Clear form
      ['port-symbol','port-name','port-qty','port-price'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = '';
      });
      await loadPortfolio();
    }
  } catch(e) {
    alert('Error adding holding: ' + e.message);
  }
}

async function removeHolding(id) {
  if (!confirm('Remove this holding?')) return;
  try {
    await fetch(`${API}/api/portfolio/${id}`, { method: 'DELETE' });
    await loadPortfolio();
  } catch(e) {
    alert('Error removing holding');
  }
}

function prefillForm(symbol) {
  const nameMap = {
    'RELIANCE.NS':'Reliance Industries', 'TCS.NS':'Tata Consultancy',
    'INFY.NS':'Infosys',                 'HDFCBANK.NS':'HDFC Bank',
    'ICICIBANK.NS':'ICICI Bank',         'WIPRO.NS':'Wipro',
    'SBIN.NS':'State Bank of India',     'BAJFINANCE.NS':'Bajaj Finance',
    'TATAMOTORS.NS':'Tata Motors',       'ZOMATO.NS':'Zomato',
    'AAPL':'Apple Inc',                  'BTC-USD':'Bitcoin',
  };
  const symEl  = document.getElementById('port-symbol');
  const nameEl = document.getElementById('port-name');
  if (symEl)  symEl.value  = symbol;
  if (nameEl) nameEl.value = nameMap[symbol] || symbol;
  async function autoFetchName() {
  const symbolEl = document.getElementById('port-symbol');
  const nameEl   = document.getElementById('port-name');
  if (!symbolEl || !nameEl) return;

  let symbol = symbolEl.value.trim();
  if (!symbol) return;

  // Auto add .NS for Indian stocks
  if (!symbol.includes('.') && !symbol.includes('-') && !symbol.includes('=')) {
    symbol = symbol + '.NS';
    symbolEl.value = symbol;
  }

  nameEl.value = '⏳ Fetching...';

  try {
    const res  = await fetch(`${API}/api/stock-info/${encodeURIComponent(symbol)}`);
    const json = await res.json();
    if (json.name) {
      nameEl.value = json.name;
    } else {
      nameEl.value = symbol.replace('.NS','').replace('.BO','');
    }
  } catch(e) {
    nameEl.value = symbol.replace('.NS','').replace('.BO','');
  }
}
}
const symbols = [
  'RELIANCE.NS','TCS.NS','INFY.NS','HDFCBANK.NS',
  'ICICIBANK.NS','WIPRO.NS','SBIN.NS','BAJFINANCE.NS',
  'TATAMOTORS.NS','ZOMATO.NS','AAPL','BTC-USD'
];

const container = document.getElementById("quick-add");

if (container) {
  container.innerHTML = symbols
    .map(s => `
      <span class="quick-chip" onclick="prefillForm('${s}')">
        ${s.replace('.NS','')}
      </span>
    `)
    .join('');
}
// ── AI Brief ──────────────────────────────────────────────────────────────
async function loadAIBrief() {
  const el  = document.getElementById('ai-brief-content');
  const btn = document.getElementById('brief-btn');
  if (!el) return;

  // Loading state
  el.innerHTML = `
    <div class="ai-loading">
      <div class="ai-loading-dot"></div>
      <div class="ai-loading-dot"></div>
      <div class="ai-loading-dot"></div>
      <span>AI is analyzing markets...</span>
    </div>`;
  if (btn) btn.disabled = true;

  try {
    const res  = await fetch(`${API}/api/ai/brief`);
    const json = await res.json();

    if (json.status === 'error') {
      el.innerHTML = `<div style="padding:20px;color:var(--red)">${json.brief}</div>`;
      return;
    }

    // Format the brief nicely
    const formatted = formatAIBrief(json.brief);
    const time = new Date(json.generated).toLocaleTimeString('en-IN',{timeZone:'Asia/Kolkata'});

    el.innerHTML = `
      <div class="ai-brief-body">${formatted}</div>
      <div class="ai-meta">
        <span>🤖 ${json.model}</span>
        <span>⏰ Generated at ${time} IST</span>
        <span>📊 ${json.tokens} tokens used</span>
      </div>`;

  } catch(e) {
    el.innerHTML = `<div style="padding:20px;color:var(--red)">Error: ${e.message}</div>`;
  } finally {
    if (btn) btn.disabled = false;
  }
}

function formatAIBrief(text) {
  const lines = text.split('\n');
  let html = '';
  lines.forEach(line => {
    line = line.trim();
    if (!line) { html += '<div style="height:8px"></div>'; return; }
    // Remove markdown bold
    line = line.replace(/\*\*(.*?)\*\*/g, '<strong style="color:var(--text-pri)">$1</strong>');
    line = line.replace(/\*(.*?)\*/g, '<em>$1</em>');
    // Numbered section headers
    if (/^\d+\.\s+[A-Z]/.test(line)) {
      html += `<div class="ai-brief-header" style="margin-top:16px">${line}</div>`;
    }
    // Bullet points
    else if (line.startsWith('•') || line.startsWith('-') || line.startsWith('*')) {
      html += `<div style="padding:4px 0 4px 20px;color:var(--text-sec);font-size:0.87rem">
        <span style="color:var(--accent);margin-right:6px">▸</span>${line.slice(1).trim()}
      </div>`;
    }
    else {
      html += `<div style="margin:4px 0;font-size:0.88rem;color:var(--text-sec);line-height:1.7">${line}</div>`;
    }
  });
  return html;
}

function formatAIText(text) {
  // Generic formatter — removes markdown, formats bullets
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong style="color:var(--text-pri)">$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/^[-•]\s/gm, '<span style="color:var(--accent)">▸</span> ')
    .replace(/\n/g, '<br/>');
}

async function loadAISentiment() {
  const el  = document.getElementById('ai-sentiment-content');
  const btn = document.getElementById('sentiment-btn');
  if (!el) return;

  el.innerHTML = `
    <div class="ai-loading">
      <div class="ai-loading-dot"></div>
      <div class="ai-loading-dot"></div>
      <div class="ai-loading-dot"></div>
      <span>Running deep analysis...</span>
    </div>`;
  if (btn) btn.disabled = true;

  try {
    const res  = await fetch(`${API}/api/ai/sentiment`);
    const json = await res.json();

    // Format sentiment report with sections
    const formatted = formatSentimentReport(json.summary);
    el.innerHTML = `
      <div style="padding:16px;max-height:500px;overflow-y:auto">
        ${formatted}
      </div>
      <div class="ai-meta">
        <span>🤖 Llama 3.3 70B</span>
        <span>📊 ${json.tokens || '--'} tokens</span>
      </div>`;
  } catch(e) {
    el.innerHTML = `<div style="padding:16px;color:var(--red)">Error: ${e.message}</div>`;
  } finally {
    if (btn) btn.disabled = false;
  }
}

function formatSentimentReport(text) {
  const lines = text.split('\n');
  let html = '';
  lines.forEach(line => {
    line = line.trim();
    if (!line) { html += '<div style="height:6px"></div>'; return; }
    line = line.replace(/\*\*(.*?)\*\*/g,'<strong style="color:var(--text-pri)">$1</strong>');
    line = line.replace(/\*(.*?)\*/g,'<em>$1</em>');

    // Section headers
    if (/^\d+\.\s+[A-Z]/.test(line)) {
      html += `<div style="font-size:0.75rem;font-weight:700;color:var(--accent);
        text-transform:uppercase;letter-spacing:0.5px;
        padding:10px 0 5px;border-bottom:1px solid var(--border);
        margin-bottom:6px">${line}</div>`;
    }
    // Probability lines
    else if (line.includes('%') && (line.includes('Bullish') || line.includes('Bearish') ||
             line.includes('Sideways') || line.includes('Appreciation') ||
             line.includes('Rally') || line.includes('probability'))) {
      const match = line.match(/(\d+)%/);
      const pct   = match ? parseInt(match[1]) : 0;
      const color = pct >= 60 ? 'var(--green)' : pct >= 40 ? 'var(--yellow)' : 'var(--red)';
      html += `<div style="display:flex;align-items:center;gap:10px;
        padding:6px 0;border-bottom:1px solid var(--border)">
        <div style="font-size:0.83rem;color:var(--text-sec);flex:1">${line.replace(/(\d+%)/g,
          '<strong style="color:'+color+'">$1</strong>')}</div>
        <div style="width:80px;height:6px;background:var(--bg-base);
          border-radius:3px;overflow:hidden">
          <div style="width:${pct}%;height:100%;background:${color};
            border-radius:3px;transition:width 1s"></div>
        </div>
      </div>`;
    }
    // BULLISH/BEARISH/NEUTRAL labels
    else if (line.includes('BULLISH') || line.includes('BEARISH') || line.includes('NEUTRAL')) {
      const col = line.includes('BULLISH') ? 'var(--green)'
               : line.includes('BEARISH') ? 'var(--red)'
               : 'var(--text-dim)';
      html += `<div style="padding:5px 0;font-size:0.84rem;color:var(--text-sec)">
        ${line.replace(/(BULLISH|BEARISH|NEUTRAL)/g,
          `<span style="color:${col};font-weight:700">$1</span>`)}
      </div>`;
    }
    // HIGH/MEDIUM/LOW ratings
    else if (line.includes('HIGH') || line.includes('MEDIUM') || line.includes('LOW')) {
      const col = line.includes('HIGH') ? 'var(--red)'
               : line.includes('MEDIUM') ? 'var(--yellow)'
               : 'var(--green)';
      html += `<div style="padding:4px 0;font-size:0.84rem;color:var(--text-sec)">
        ${line.replace(/(HIGH|MEDIUM|LOW)/g,
          `<span style="color:${col};font-weight:700;font-size:0.75rem;
           background:var(--bg-base);padding:1px 6px;border-radius:4px">$1</span>`)}
      </div>`;
    }
    // Bullets
    else if (line.startsWith('-') || line.startsWith('•')) {
      html += `<div style="padding:3px 0 3px 14px;font-size:0.84rem;color:var(--text-sec)">
        <span style="color:var(--accent)">▸</span> ${line.slice(1).trim()}
      </div>`;
    }
    else {
      html += `<div style="font-size:0.84rem;color:var(--text-sec);
        padding:3px 0;line-height:1.6">${line}</div>`;
    }
  });
  return html;
}
async function analyzeEvent() {
  const input = document.getElementById('event-input');
  const el    = document.getElementById('event-analysis');
  if (!input || !el) return;

  const event = input.value.trim();
  if (!event) { alert('Please describe an event to analyze'); return; }

  el.innerHTML = `
    <div class="ai-loading">
      <div class="ai-loading-dot"></div>
      <div class="ai-loading-dot"></div>
      <div class="ai-loading-dot"></div>
      <span>Analyzing impact...</span>
    </div>`;

  try {
    const res  = await fetch(`${API}/api/ai/impact`, {
      method:  'POST',
      headers: {'Content-Type':'application/json'},
      body:    JSON.stringify({ event })
    });
    const json = await res.json();

    el.innerHTML = `
      <div class="event-analysis-card">
        <div style="font-size:0.75rem;color:var(--accent);
          font-weight:700;margin-bottom:8px">⚡ IMPACT ANALYSIS</div>
        ${json.analysis}
      </div>`;
  } catch(e) {
    el.innerHTML = `<div style="color:var(--red)">Error: ${e.message}</div>`;
  }
}
async function askAI() {
  const input = document.getElementById('ai-question');
  const el    = document.getElementById('ai-answer');
  if (!input || !el) return;

  const question = input.value.trim();
  if (!question) return;

  el.innerHTML = `
    <div class="ai-loading">
      <div class="ai-loading-dot"></div>
      <div class="ai-loading-dot"></div>
      <div class="ai-loading-dot"></div>
      <span>Thinking...</span>
    </div>`;

  try {
    const res  = await fetch(`${API}/api/ai/ask`, {
      method:  'POST',
      headers: {'Content-Type':'application/json'},
      body:    JSON.stringify({ question })
    });
    const json = await res.json();
    el.innerHTML = `
      <div class="event-analysis-card">
        <div style="font-size:0.72rem;color:var(--accent);
          font-weight:700;margin-bottom:8px;letter-spacing:0.5px">
          🤖 AI RESPONSE
        </div>
        <div style="font-size:0.87rem;color:var(--text-sec);line-height:1.7">
          ${formatAIText(json.answer)}
        </div>
      </div>`;
  } catch(e) {
    el.innerHTML = `<div style="color:var(--red)">Error: ${e.message}</div>`;
  }
}
// ── Probability Dashboard ─────────────────────────────────────────────────
let probData       = null;
let selectedAsset  = 'NIFTY 50';

async function loadProbabilityData() {
  try {
    const res = await fetch(`${API}/api/probability`);
    probData  = await res.json();
    renderBreadthPanel(probData.market_breadth);
    renderVixPanel(probData.vix_proxy);
    renderAssetAnalysis(selectedAsset);
    renderVolRanking(probData.vix_proxy?.assets || []);
  } catch(e) {
    console.error('Probability error:', e);
  }
}

function selectProbAsset(name, el) {
  selectedAsset = name;
  document.querySelectorAll('.active-chip').forEach(c => {
    c.classList.remove('active-chip');
  });
  if (el) el.classList.add('active-chip');
  renderAssetAnalysis(name);
}

function renderBreadthPanel(breadth) {
  const el = document.getElementById('breadth-panel');
  if (!el || !breadth || !breadth.total) {
    if (el) el.innerHTML = '<div style="padding:20px;color:var(--text-dim)">Not enough data yet — keep scheduler running</div>';
    return;
  }

  const sig   = breadth.breadth_signal || 'NEUTRAL';
  const color = sig.includes('BULLISH') ? 'var(--green)'
              : sig.includes('BEARISH') ? 'var(--red)'
              : 'var(--yellow)';

  el.innerHTML = `
    <div style="padding:20px;text-align:center">
      <div style="font-size:2rem;font-weight:800;color:${color};margin-bottom:4px">
        ${sig}
      </div>
      <div style="font-size:0.82rem;color:var(--text-dim);margin-bottom:16px">
        Market Breadth Score: <strong style="color:${color}">${breadth.breadth_score}/100</strong>
      </div>
    </div>

    <div style="padding:0 16px 16px">
      <!-- Advance/Decline bar -->
      <div style="display:flex;height:24px;border-radius:6px;overflow:hidden;margin-bottom:10px">
        <div style="width:${breadth.advancing_pct}%;background:var(--green);
          display:flex;align-items:center;justify-content:center;
          font-size:0.75rem;font-weight:700;color:#fff">
          ${breadth.advancing_pct > 15 ? breadth.advancing + ' ▲' : ''}
        </div>
        <div style="width:${breadth.declining_pct}%;background:var(--red);
          display:flex;align-items:center;justify-content:center;
          font-size:0.75rem;font-weight:700;color:#fff">
          ${breadth.declining_pct > 15 ? breadth.declining + ' ▼' : ''}
        </div>
      </div>

      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;text-align:center">
        <div style="background:var(--bg-base);border-radius:6px;padding:10px">
          <div style="color:var(--green);font-size:1.2rem;font-weight:800">${breadth.advancing}</div>
          <div style="color:var(--text-dim);font-size:0.72rem">Advancing</div>
        </div>
        <div style="background:var(--bg-base);border-radius:6px;padding:10px">
          <div style="color:var(--red);font-size:1.2rem;font-weight:800">${breadth.declining}</div>
          <div style="color:var(--text-dim);font-size:0.72rem">Declining</div>
        </div>
        <div style="background:var(--bg-base);border-radius:6px;padding:10px">
          <div style="color:var(--text-dim);font-size:1.2rem;font-weight:800">${breadth.unchanged}</div>
          <div style="color:var(--text-dim);font-size:0.72rem">Unchanged</div>
        </div>
      </div>

      <div style="margin-top:10px;font-size:0.8rem;color:var(--text-dim);text-align:center">
        A/D Ratio: <strong style="color:var(--text-pri)">${breadth.adv_dec_ratio}</strong>
      </div>
    </div>`;
}

function renderVixPanel(vix) {
  const el = document.getElementById('vix-panel');
  if (!el || !vix) return;

  const val   = vix.vix_proxy || 20;
  const sig   = vix.signal    || 'NORMAL';
  const color = vix.color     || 'var(--yellow)';
  const pct   = Math.min(val / 60 * 100, 100);

  el.innerHTML = `
    <div style="padding:20px;text-align:center">
      <div style="font-size:3rem;font-weight:800;font-family:monospace;
        color:${color};margin-bottom:4px">${val}</div>
      <div style="font-size:1rem;font-weight:700;color:${color};
        margin-bottom:16px">${sig}</div>

      <!-- VIX gauge bar -->
      <div style="background:linear-gradient(90deg,#00c896,#ffb800,#ff9800,#ff4560);
        height:12px;border-radius:6px;position:relative;margin:0 16px 8px">
        <div style="position:absolute;top:-4px;left:${pct}%;
          transform:translateX(-50%);width:4px;height:20px;
          background:#fff;border-radius:2px;box-shadow:0 0 6px rgba(255,255,255,0.6)"></div>
      </div>
      <div style="display:flex;justify-content:space-between;
        font-size:0.65rem;color:var(--text-dim);padding:0 16px;margin-bottom:16px">
        <span>Complacent</span><span>Normal</span><span>Fear</span><span>Extreme</span>
      </div>
    </div>

    <div style="padding:0 16px 16px">
      <div style="font-size:0.72rem;color:var(--text-dim);
        font-weight:700;letter-spacing:0.5px;margin-bottom:8px">
        MOST VOLATILE ASSETS
      </div>
      ${(vix.assets || []).slice(0,5).map(a => {
        const v   = a.vol || 0;
        const col = v >= 40 ? 'var(--red)' : v >= 25 ? 'var(--yellow)' : 'var(--green)';
        return `<div class="vol-row">
          <div style="font-size:0.82rem;color:var(--text-sec);min-width:120px">${a.name}</div>
          <div class="vol-bar-wrap">
            <div class="vol-bar" style="width:${Math.min(v/60*100,100)}%;background:${col}"></div>
          </div>
          <div style="font-size:0.8rem;font-weight:700;font-family:monospace;
            color:${col};min-width:50px;text-align:right">${v}%</div>
        </div>`;
      }).join('')}
    </div>`;
}

function renderAssetAnalysis(assetName) {
  if (!probData || !probData.assets || !probData.assets[assetName]) {
    const msg = '<div style="padding:20px;color:var(--text-dim)">Not enough historical data yet — keep scheduler running for a few hours.</div>';
    ['expected-move-cards','sr-levels','trend-panel'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.innerHTML = msg;
    });
    return;
  }

  const data = probData.assets[assetName];
  renderExpectedMove(data.expected_move);
  renderSupportResistance(data.support_resistance);
  renderTrendPanel(data.trend, data.volatility);
}

function renderExpectedMove(em) {
  const el = document.getElementById('expected-move-cards');
  if (!el || !em || !em.current_price) {
    if (el) el.innerHTML = '<div style="color:var(--text-dim);padding:10px">No data</div>';
    return;
  }

  const periods = [
    { key:'expected_move_1d',  label:'1 Day',   emoji:'📅' },
    { key:'expected_move_5d',  label:'5 Days',  emoji:'📆' },
    { key:'expected_move_30d', label:'30 Days', emoji:'🗓️' },
  ];

  el.innerHTML = periods.map(p => {
    const d = em[p.key];
    if (!d) return '';
    return `<div class="prob-card">
      <div class="prob-card-label">${p.emoji} Expected Move — ${p.label}</div>
      <div class="prob-card-value" style="color:var(--accent2)">
        ±${d.pct}%
      </div>
      <div class="prob-card-sub">±${d.points.toLocaleString('en-IN')} points</div>
      <div style="margin-top:12px">
        <div style="display:flex;justify-content:space-between;
          font-size:0.78rem;margin-bottom:4px">
          <span style="color:var(--green)">▲ ${d.upper.toLocaleString('en-IN')}</span>
          <span style="color:var(--text-dim)">Current: ${em.current_price.toLocaleString('en-IN')}</span>
          <span style="color:var(--red)">▼ ${d.lower.toLocaleString('en-IN')}</span>
        </div>
        <!-- Range bar -->
        <div style="height:8px;background:linear-gradient(90deg,
          var(--red),var(--yellow),var(--green));
          border-radius:4px;position:relative">
          <div style="position:absolute;left:50%;top:-3px;
            transform:translateX(-50%);width:3px;height:14px;
            background:#fff;border-radius:2px"></div>
        </div>
      </div>
    </div>`;
  }).join('');
}

function renderSupportResistance(sr) {
  const el = document.getElementById('sr-levels');
  if (!el || !sr || !sr.current) {
    if (el) el.innerHTML = '<div style="color:var(--text-dim);padding:10px">No data</div>';
    return;
  }

  const levels = [
    { label:'R2', value:sr.resistance?.r2, color:'#ff4560', bg:'#200d0d' },
    { label:'R1', value:sr.resistance?.r1, color:'#ff9800', bg:'#281a0d' },
    { label:'PIVOT', value:sr.pivot,        color:'#4fc3f7', bg:'#0d1e2e' },
    { label:'S1', value:sr.support?.s1,     color:'#8bc34a', bg:'#162010' },
    { label:'S2', value:sr.support?.s2,     color:'#00c896', bg:'#0d2018' },
  ];

  el.innerHTML = `
    <div class="sr-grid">
      ${levels.map(l => `
        <div class="sr-level" style="background:${l.bg};border-color:${l.color}33">
          <div class="sr-level-label" style="color:${l.color}">${l.label}</div>
          <div class="sr-level-value" style="color:${l.color}">
            ${l.value ? l.value.toLocaleString('en-IN') : '--'}
          </div>
        </div>`).join('')}

      <div class="sr-level" style="background:var(--bg-hover);border-color:var(--border-lit)">
        <div class="sr-level-label" style="color:var(--text-dim)">RANGE</div>
        <div style="font-size:0.75rem;color:var(--text-sec);margin-top:4px">
          H: ${sr.range?.high?.toLocaleString('en-IN') || '--'}<br/>
          L: ${sr.range?.low?.toLocaleString('en-IN')  || '--'}
        </div>
      </div>
    </div>

    <div style="display:flex;gap:10px;margin-top:10px;font-size:0.78rem;color:var(--text-dim)">
      <span>📈 From Low: <strong style="color:var(--green)">
        ${sr.distance_from_low_pct >= 0 ? '+' : ''}${sr.distance_from_low_pct}%
      </strong></span>
      <span>📉 From High: <strong style="color:var(--red)">
        ${sr.distance_from_high_pct}%
      </strong></span>
    </div>`;
}

function renderTrendPanel(trend, vol) {
  const el = document.getElementById('trend-panel');
  if (!el || !trend) return;

  const trendColor = trend.trend_score >= 60 ? 'var(--green)'
                   : trend.trend_score <= 40 ? 'var(--red)'
                   : 'var(--yellow)';

  const rsiColor = trend.rsi >= 70 ? 'var(--red)'
                 : trend.rsi <= 30 ? 'var(--green)'
                 : 'var(--text-sec)';

  el.innerHTML = `
    <!-- Trend -->
    <div style="padding:16px;text-align:center;border-bottom:1px solid var(--border)">
      <div style="font-size:1.3rem;font-weight:800;color:${trendColor}">
        ${trend.trend}
      </div>
      <div style="margin-top:8px;height:8px;background:var(--bg-base);
        border-radius:4px;overflow:hidden">
        <div style="width:${trend.trend_score}%;height:100%;
          background:${trendColor};border-radius:4px;transition:width 1s"></div>
      </div>
      <div style="font-size:0.75rem;color:var(--text-dim);margin-top:4px">
        Trend Strength: ${trend.trend_score}/100
      </div>
    </div>

    <!-- RSI -->
    <div class="trend-row">
      <div style="font-size:0.85rem;color:var(--text-sec)">RSI (14)</div>
      <div>
        <span style="font-size:1rem;font-weight:700;font-family:monospace;
          color:${rsiColor}">${trend.rsi}</span>
        <span style="font-size:0.72rem;color:var(--text-dim);margin-left:6px">
          ${trend.rsi >= 70 ? 'Overbought' : trend.rsi <= 30 ? 'Oversold' : 'Normal'}
        </span>
      </div>
    </div>

    <!-- Moving Averages -->
    <div class="trend-row">
      <div style="font-size:0.85rem;color:var(--text-sec)">MA 5</div>
      <div style="font-family:monospace;font-size:0.85rem">
        ${trend.ma_5?.toLocaleString('en-IN')}
        <span style="font-size:0.75rem;color:${trend.vs_ma5_pct>=0?'var(--green)':'var(--red)'}">
          (${trend.vs_ma5_pct >= 0 ? '+' : ''}${trend.vs_ma5_pct}%)
        </span>
      </div>
    </div>
    <div class="trend-row">
      <div style="font-size:0.85rem;color:var(--text-sec)">MA 20</div>
      <div style="font-family:monospace;font-size:0.85rem">
        ${trend.ma_20?.toLocaleString('en-IN')}
        <span style="font-size:0.75rem;color:${trend.vs_ma20_pct>=0?'var(--green)':'var(--red)'}">
          (${trend.vs_ma20_pct >= 0 ? '+' : ''}${trend.vs_ma20_pct}%)
        </span>
      </div>
    </div>

    <!-- Volatility -->
    ${vol ? `
    <div class="trend-row">
      <div style="font-size:0.85rem;color:var(--text-sec)">Daily Vol</div>
      <div style="font-family:monospace;font-size:0.85rem;color:var(--yellow)">
        ±${vol.daily_vol}%
      </div>
    </div>
    <div class="trend-row" style="border:none">
      <div style="font-size:0.85rem;color:var(--text-sec)">Annual Vol</div>
      <div style="font-family:monospace;font-size:0.85rem;color:var(--yellow)">
        ${vol.annual_vol}%
      </div>
    </div>` : ''}`;
}

function renderVolRanking(assets) {
  const el = document.getElementById('vol-ranking');
  if (!el || !assets.length) {
    if (el) el.innerHTML = '<div style="padding:16px;color:var(--text-dim)">Not enough data yet.</div>';
    return;
  }

  const maxVol = Math.max(...assets.map(a => a.vol));
  el.innerHTML = assets.map(a => {
    const pct = (a.vol / maxVol) * 100;
    const col = a.vol >= 40 ? 'var(--red)'
              : a.vol >= 25 ? 'var(--yellow)'
              : 'var(--green)';
    return `<div class="vol-row">
      <div style="font-size:0.82rem;color:var(--text-sec);min-width:130px">${a.name}</div>
      <div class="vol-bar-wrap">
        <div class="vol-bar" style="width:${pct}%;background:${col}"></div>
      </div>
      <div style="font-size:0.8rem;font-weight:700;font-family:monospace;
        color:${col};min-width:55px;text-align:right">${a.vol}% ann.</div>
    </div>`;
  }).join('');
}
// ── Screener ──────────────────────────────────────────────────────────────
let screenerData  = [];
let screenerSort  = 'change_pct';
let screenerOrder = 'desc';

async function loadScreener() {
  const el = document.getElementById('screener-table');
  if (el) el.innerHTML = '<div style="padding:30px;text-align:center;color:var(--text-dim)">⏳ Loading...</div>';

  try {
    const res    = await fetch(`${API}/api/screener`);
    const json   = await res.json();
    screenerData = json.data || [];
    applyScreener();
  } catch(e) {
    if (el) el.innerHTML = `<div style="padding:20px;color:var(--red)">Error: ${e.message}</div>`;
  }
}

function applyScreener() {
  const type   = document.getElementById('scr-type')?.value   || 'all';
  const trend  = document.getElementById('scr-trend')?.value  || 'all';
  const signal = document.getElementById('scr-signal')?.value || 'all';
  const rsiF   = document.getElementById('scr-rsi')?.value    || 'all';
  const chgMin = parseFloat(document.getElementById('scr-change')?.value || '0');
  const sort   = document.getElementById('scr-sort')?.value   || 'change_pct';

  screenerSort = sort;

  let filtered = [...screenerData];

  // Filters
  if (type   !== 'all') filtered = filtered.filter(a => a.asset_type === type);
  if (trend  !== 'all') filtered = filtered.filter(a => a.trend === trend);
  if (signal !== 'all') filtered = filtered.filter(a => a.signal === signal);
  if (chgMin > 0)       filtered = filtered.filter(a => Math.abs(a.change_pct) >= chgMin);

  if (rsiF === 'overbought') filtered = filtered.filter(a => a.rsi > 70);
  if (rsiF === 'oversold')   filtered = filtered.filter(a => a.rsi < 30);
  if (rsiF === 'neutral')    filtered = filtered.filter(a => a.rsi >= 30 && a.rsi <= 70);

  // Sort
  filtered.sort((a, b) => {
    const valA = Math.abs(a[sort]);
    const valB = Math.abs(b[sort]);
    return screenerOrder === 'desc' ? valB - valA : valA - valB;
  });

  renderScreenerTable(filtered);
}

function renderScreenerTable(data) {
  const el       = document.getElementById('screener-table');
  const countEl  = document.getElementById('scr-count');
  if (!el) return;
  if (countEl) countEl.textContent = `${data.length} assets`;

  if (!data.length) {
    el.innerHTML = '<div style="padding:30px;text-align:center;color:var(--text-dim)">No assets match your filters.</div>';
    return;
  }

  const typeEmoji = {
    'indian_index': '🇮🇳',
    'global_index': '🌍',
    'commodity':    '🛢️',
    'forex':        '💱',
    'crypto':       '₿',
    'bond':         '📈',
  };

  el.innerHTML = `
    <div style="overflow-x:auto">
    <table class="screener-table">
      <thead>
        <tr>
          <th onclick="sortScreener('name')">Asset ↕</th>
          <th>Type</th>
          <th onclick="sortScreener('price')">Price ↕</th>
          <th onclick="sortScreener('change_pct')">Change % ↕</th>
          <th onclick="sortScreener('rsi')">RSI ↕</th>
          <th>Trend</th>
          <th>Signal</th>
          <th onclick="sortScreener('volatility')">Volatility ↕</th>
          <th>MA5</th>
          <th>MA20</th>
        </tr>
      </thead>
      <tbody>
        ${data.map(a => {
          const chg     = a.change_pct || 0;
          const chgCol  = chg > 0 ? 'var(--green)' : chg < 0 ? 'var(--red)' : 'var(--text-dim)';
          const rsiCol  = a.rsi > 70 ? 'var(--red)' : a.rsi < 30 ? 'var(--green)' : 'var(--text-sec)';
          const rsiPct  = Math.min(a.rsi, 100);
          const rsiBarCol = a.rsi > 70 ? 'var(--red)' : a.rsi < 30 ? 'var(--green)' : 'var(--accent)';
          const trendCol = a.trend.includes('BULL') ? 'var(--green)'
                         : a.trend.includes('BEAR') ? 'var(--red)'
                         : 'var(--text-dim)';
          const aboveMA5  = a.price > a.ma5;
          const aboveMA20 = a.price > a.ma20;

          return `<tr>
            <td>
              <div style="font-weight:600;color:var(--text-pri)">${a.name}</div>
              <div style="font-size:0.7rem;color:var(--text-dim)">${a.symbol}</div>
            </td>
            <td style="color:var(--text-dim)">
              ${typeEmoji[a.asset_type] || '📌'}
            </td>
            <td style="font-family:monospace;color:var(--text-pri)">
              ${Number(a.price).toLocaleString('en-IN', {maximumFractionDigits:2})}
            </td>
            <td>
              <span style="font-family:monospace;font-weight:700;color:${chgCol}">
                ${chg >= 0 ? '▲' : '▼'} ${Math.abs(chg).toFixed(2)}%
              </span>
            </td>
            <td>
              <span style="font-family:monospace;color:${rsiCol}">${a.rsi}</span>
              <span class="rsi-bar">
                <span class="rsi-fill"
                  style="width:${rsiPct}%;background:${rsiBarCol}"></span>
              </span>
            </td>
            <td style="color:${trendCol};font-size:0.8rem;font-weight:600">
              ${a.trend}
            </td>
            <td>
              <span class="signal-badge signal-${a.signal}">${a.signal}</span>
            </td>
            <td style="font-family:monospace;color:var(--yellow)">
              ${a.volatility > 0 ? '±' + a.volatility + '%' : '--'}
            </td>
            <td style="font-family:monospace;font-size:0.8rem;
              color:${aboveMA5?'var(--green)':'var(--red)'}">
              ${Number(a.ma5).toLocaleString('en-IN',{maximumFractionDigits:2})}
            </td>
            <td style="font-family:monospace;font-size:0.8rem;
              color:${aboveMA20?'var(--green)':'var(--red)'}">
              ${Number(a.ma20).toLocaleString('en-IN',{maximumFractionDigits:2})}
            </td>
          </tr>`;
        }).join('')}
      </tbody>
    </table>
    </div>`;
}

function sortScreener(field) {
  if (screenerSort === field) {
    screenerOrder = screenerOrder === 'desc' ? 'asc' : 'desc';
  } else {
    screenerSort  = field;
    screenerOrder = 'desc';
  }
  document.getElementById('scr-sort').value = field;
  applyScreener();
}

function presetScreener(preset) {
  // Reset all filters first
  resetScreener(false);

  const typeEl   = document.getElementById('scr-type');
  const trendEl  = document.getElementById('scr-trend');
  const signalEl = document.getElementById('scr-signal');
  const rsiEl    = document.getElementById('scr-rsi');
  const sortEl   = document.getElementById('scr-sort');

  if (preset === 'gainers') {
    sortEl.value   = 'change_pct';
    screenerOrder  = 'desc';
  } else if (preset === 'losers') {
    sortEl.value   = 'change_pct';
    screenerOrder  = 'desc';
    // We'll handle this by showing negatives
  } else if (preset === 'oversold') {
    rsiEl.value    = 'oversold';
    signalEl.value = 'BUY';
  } else if (preset === 'overbought') {
    rsiEl.value    = 'overbought';
  } else if (preset === 'volatile') {
    sortEl.value   = 'volatility';
    screenerOrder  = 'desc';
  } else if (preset === 'bullish') {
    trendEl.value  = 'BULLISH';
    signalEl.value = 'BUY';
  }

  // Highlight active preset
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  event.target.classList.add('active');

  applyScreener();
}

function resetScreener(resetPresets = true) {
  ['scr-type','scr-trend','scr-signal','scr-rsi','scr-change'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = 'all';
  });
  const sortEl = document.getElementById('scr-sort');
  if (sortEl) sortEl.value = 'change_pct';
  screenerOrder = 'desc';
  if (resetPresets) {
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  }
  applyScreener();
}

function exportCSV() {
  const type  = document.getElementById('scr-type')?.value  || 'all';
  let filtered = type === 'all' ? screenerData
    : screenerData.filter(a => a.asset_type === type);

  const headers = ['Name','Symbol','Type','Price','Change%','RSI','Trend','Signal','Volatility','MA5','MA20'];
  const rows    = filtered.map(a => [
    a.name, a.symbol, a.asset_type,
    a.price, a.change_pct, a.rsi,
    a.trend, a.signal, a.volatility,
    a.ma5, a.ma20
  ]);

  const csv  = [headers, ...rows].map(r => r.join(',')).join('\n');
  const blob = new Blob([csv], { type:'text/csv' });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href     = url;
  a.download = `fintrack_screener_${new Date().toISOString().slice(0,10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}
// ── Watchlist ─────────────────────────────────────────────────────────────
let watchlistData = [];

async function loadWatchlist() {
  const el = document.getElementById('wl-table');
  if (el) el.innerHTML = '<div style="padding:20px;color:var(--text-dim)">⏳ Loading...</div>';

  try {
    const res  = await fetch(`${API}/api/watchlist`);
    const json = await res.json();
    watchlistData = json.data || [];
    renderWatchlistTable(watchlistData);
    renderAlertsBanner(watchlistData);
    loadAlertHistory();
  } catch(e) {
    if (el) el.innerHTML = `<div style="padding:20px;color:var(--red)">Error: ${e.message}</div>`;
  }
}

function renderAlertsBanner(items) {
  const el       = document.getElementById('wl-alerts-banner');
  if (!el) return;
  const triggered = items.filter(i => i.alerts_triggered?.length > 0);

  if (!triggered.length) { el.innerHTML = ''; return; }

  el.innerHTML = triggered.map(item =>
    item.alerts_triggered.map(a => `
      <div class="alert-banner" style="margin-bottom:8px">
        <div class="alert-banner-icon">🚨</div>
        <div class="alert-banner-text">
          <strong style="color:var(--red)">${item.name}</strong>
          is currently at
          <strong>₹${a.current.toLocaleString('en-IN')}</strong>
          — ${a.type === 'ABOVE' ? '🔺 Above' : '🔻 Below'} your target of
          <strong>₹${a.target.toLocaleString('en-IN')}</strong>
        </div>
      </div>`).join('')
  ).join('');
}

function renderWatchlistTable(items) {
  const el = document.getElementById('wl-table');
  if (!el) return;

  if (!items.length) {
    el.innerHTML = '<div style="padding:40px;text-align:center;color:var(--text-dim)">No assets in watchlist yet. Add some above ☝️</div>';
    return;
  }

  el.innerHTML = `
    <table class="wl-table">
      <thead>
        <tr>
          <th>Asset</th>
          <th>Live Price</th>
          <th>Alert Above</th>
          <th>Alert Below</th>
          <th>Distance</th>
          <th>Status</th>
          <th>Notes</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        ${items.map(item => {
          const triggered = item.alerts_triggered?.length > 0;
          const price     = item.live_price || 0;

          // Distance badge
          let distHTML = '<span style="color:var(--text-dim)">--</span>';
          if (item.dist_above_pct !== null && item.dist_above_pct !== undefined) {
            const d   = item.dist_above_pct;
            const cls = d <= 2 ? 'dist-close' : d <= 5 ? 'dist-medium' : 'dist-far';
            distHTML  = `<span class="dist-badge ${cls}">↑ ${d}% to target</span>`;
          } else if (item.dist_below_pct !== null && item.dist_below_pct !== undefined) {
            const d   = item.dist_below_pct;
            const cls = d <= 2 ? 'dist-close' : d <= 5 ? 'dist-medium' : 'dist-far';
            distHTML  = `<span class="dist-badge ${cls}">↓ ${d}% to target</span>`;
          }

          return `<tr class="${triggered ? 'alert-triggered' : ''}">
            <td>
              <div style="font-weight:600;color:var(--text-pri)">${item.name}</div>
              <div style="font-size:0.72rem;color:var(--text-dim)">${item.symbol}</div>
            </td>
            <td style="font-family:monospace;font-size:0.95rem;
              color:var(--accent2);font-weight:700">
              ₹${price.toLocaleString('en-IN', {maximumFractionDigits:2})}
            </td>
            <td style="font-family:monospace;color:var(--green)">
              ${item.alert_above
                ? `▲ ₹${Number(item.alert_above).toLocaleString('en-IN')}`
                : '<span style="color:var(--text-dim)">--</span>'}
            </td>
            <td style="font-family:monospace;color:var(--red)">
              ${item.alert_below
                ? `▼ ₹${Number(item.alert_below).toLocaleString('en-IN')}`
                : '<span style="color:var(--text-dim)">--</span>'}
            </td>
            <td>${distHTML}</td>
            <td>
              ${triggered
                ? '<span style="color:var(--red);font-weight:700;font-size:0.82rem">🚨 ALERT FIRED</span>'
                : '<span style="color:var(--green);font-size:0.82rem">✅ Watching</span>'}
            </td>
            <td style="font-size:0.8rem;color:var(--text-dim);max-width:150px;
              overflow:hidden;text-overflow:ellipsis;white-space:nowrap">
              ${item.notes || '--'}
            </td>
            <td>
              <div style="display:flex;gap:6px">
                <button class="del-btn" style="color:var(--accent);border-color:var(--border)"
                  onclick="openEditModal(${item.id},${item.alert_above||'null'},
                    ${item.alert_below||'null'},'${item.notes||''}')">
                  ✏️
                </button>
                <button class="del-btn"
                  onclick="removeFromWatchlist(${item.id})">
                  🗑
                </button>
              </div>
            </td>
          </tr>`;
        }).join('')}
      </tbody>
    </table>`;
}

async function addToWatchlist() {
  const symbol = document.getElementById('wl-symbol')?.value?.trim();
  const name   = document.getElementById('wl-name')?.value?.trim();
  const type   = document.getElementById('wl-type')?.value;
  const above  = parseFloat(document.getElementById('wl-above')?.value) || null;
  const below  = parseFloat(document.getElementById('wl-below')?.value) || null;
  const notes  = document.getElementById('wl-notes')?.value?.trim() || null;

  if (!symbol || !name) {
    alert('Please enter symbol and name!');
    return;
  }

  try {
    const res  = await fetch(`${API}/api/watchlist`, {
      method:  'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({
        symbol, name, asset_type: type,
        alert_above: above,
        alert_below: below,
        notes
      })
    });
    const json = await res.json();

    if (json.status === 'exists') {
      alert(`${name} is already in your watchlist!`);
      return;
    }

    // Clear form
    ['wl-symbol','wl-name','wl-above','wl-below','wl-notes']
      .forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = '';
      });

    await loadWatchlist();
  } catch(e) {
    alert('Error: ' + e.message);
  }
}

async function removeFromWatchlist(id) {
  if (!confirm('Remove from watchlist?')) return;
  try {
    await fetch(`${API}/api/watchlist/${id}`, { method:'DELETE' });
    await loadWatchlist();
  } catch(e) {
    alert('Error: ' + e.message);
  }
}

function openEditModal(id, above, below, notes) {
  document.getElementById('edit-wl-id').value    = id;
  document.getElementById('edit-above').value    = above  || '';
  document.getElementById('edit-below').value    = below  || '';
  document.getElementById('edit-notes').value    = notes  || '';
  document.getElementById('wl-edit-modal').style.display = 'flex';
}

function closeEditModal() {
  document.getElementById('wl-edit-modal').style.display = 'none';
}

async function saveWatchlistEdit() {
  const id    = document.getElementById('edit-wl-id').value;
  const above = parseFloat(document.getElementById('edit-above').value) || null;
  const below = parseFloat(document.getElementById('edit-below').value) || null;
  const notes = document.getElementById('edit-notes').value?.trim() || null;

  try {
    await fetch(`${API}/api/watchlist/${id}`, {
      method:  'PUT',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({
        alert_above: above,
        alert_below: below,
        notes
      })
    });
    closeEditModal();
    await loadWatchlist();
  } catch(e) {
    alert('Error: ' + e.message);
  }
}

async function loadAlertHistory() {
  const el = document.getElementById('alert-history-list');
  if (!el) return;

  try {
    const res  = await fetch(`${API}/api/watchlist/alerts`);
    const json = await res.json();

    if (!json.data?.length) {
      el.innerHTML = '<div style="padding:20px;color:var(--text-dim)">No alerts triggered yet.</div>';
      return;
    }

    el.innerHTML = json.data.map(a => {
      const col  = a.alert_type === 'ABOVE' ? 'var(--green)' : 'var(--red)';
      const icon = a.alert_type === 'ABOVE' ? '🔺' : '🔻';
      const time = new Date(a.triggered_at).toLocaleString('en-IN', {
        timeZone:'Asia/Kolkata'
      });
      return `<div class="alert-hist-row">
        <div style="font-size:0.75rem;color:var(--text-dim);
          font-family:monospace">${time}</div>
        <div>
          <span style="font-weight:600;color:var(--text-pri)">${a.name}</span>
          <span style="color:${col};font-size:0.82rem;margin-left:8px">
            ${icon} ${a.alert_type}
          </span>
          <div style="font-size:0.78rem;color:var(--text-dim);margin-top:2px">
            Target: ₹${a.target_price?.toLocaleString('en-IN')}
            → Actual: ₹${a.actual_price?.toLocaleString('en-IN')}
          </div>
        </div>
        <div style="font-size:0.75rem;color:${col};font-weight:700;
          font-family:monospace">
          ${a.alert_type}
        </div>
      </div>`;
    }).join('');
  } catch(e) {}
}

async function wlAutoFetch() {
  const symEl  = document.getElementById('wl-symbol');
  const nameEl = document.getElementById('wl-name');
  if (!symEl || !nameEl) return;

  let symbol = symEl.value.trim();
  if (!symbol) return;

  if (!symbol.includes('.') && !symbol.includes('-')
      && !symbol.includes('=') && !symbol.includes('^')) {
    symbol = symbol + '.NS';
    symEl.value = symbol;
  }

  nameEl.value = '⏳ Fetching...';
  try {
    const res  = await fetch(
      `${API}/api/stock-info/${encodeURIComponent(symbol)}`
    );
    const json = await res.json();
    nameEl.value = json.name || symbol;
  } catch(e) {
    nameEl.value = symbol;
  }
}

function wlPrefill(symbol, name) {
  const symEl  = document.getElementById('wl-symbol');
  const nameEl = document.getElementById('wl-name');
  if (symEl)  symEl.value  = symbol;
  if (nameEl) nameEl.value = name;
}
// ── Quant Signals ─────────────────────────────────────────────────────────
let quantData       = null;
let selectedQuant   = { name:'NIFTY 50', symbol:'^NSEI' };

async function loadQuantData() {
  try {
    const res = await fetch(`${API}/api/quant`);
    quantData = await res.json();
    renderQuantAsset(selectedQuant.name);
  } catch(e) {
    console.error('Quant error:', e);
  }
}

function selectQuantAsset(name, symbol, el) {
  selectedQuant = { name, symbol };
  document.querySelectorAll('.active-chip')
    .forEach(c => c.classList.remove('active-chip'));
  if (el) el.classList.add('active-chip');
  renderQuantAsset(name);
}

function renderQuantAsset(name) {
  if (!quantData?.assets?.[name]) {
    const msg = '<div style="padding:20px;color:var(--text-dim)">Not enough data — keep scheduler running for a few hours.</div>';
    ['quant-signal-cards','quant-zscore','quant-momentum',
     'quant-kelly','quant-drawdown','quant-volregime',
     'quant-multirsi'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.innerHTML = msg;
    });
    return;
  }

  const d = quantData.assets[name];
  renderQuantSignalCards(d);
  renderZScore(d.zscore);
  renderMomentum(d.momentum);
  renderKelly(d.kelly);
  renderDrawdown(d.drawdown);
  renderVolRegime(d.vol_regime);
  renderMultiRSI(d.multi_rsi);
}

function renderQuantSignalCards(d) {
  const el = document.getElementById('quant-signal-cards');
  if (!el) return;

  const cards = [
    {
      label:  'Z-Score',
      value:  d.zscore?.current_z ?? '--',
      signal: d.zscore?.signal    ?? '--',
      color:  d.zscore?.current_z > 1  ? 'var(--red)'
            : d.zscore?.current_z < -1 ? 'var(--green)'
            : 'var(--text-dim)',
    },
    {
      label:  'Momentum',
      value:  d.momentum?.composite != null
              ? (d.momentum.composite >= 0 ? '+' : '')
                + d.momentum.composite + '%'
              : '--',
      signal: d.momentum?.signal ?? '--',
      color:  d.momentum?.composite > 0 ? 'var(--green)'
            : d.momentum?.composite < 0 ? 'var(--red)'
            : 'var(--text-dim)',
    },
    {
      label:  'Kelly (Half)',
      value:  d.kelly?.kelly_half != null
              ? d.kelly.kelly_half + '%' : '--',
      signal: d.kelly?.risk_level ?? '--',
      color:  d.kelly?.kelly_half > 10 ? 'var(--green)'
            : d.kelly?.kelly_half > 0  ? 'var(--yellow)'
            : 'var(--red)',
    },
    {
      label:  'Max Drawdown',
      value:  d.drawdown?.max_drawdown_pct != null
              ? d.drawdown.max_drawdown_pct + '%' : '--',
      signal: d.drawdown?.risk_rating ?? '--',
      color:  Math.abs(d.drawdown?.max_drawdown_pct || 0) > 20
              ? 'var(--red)' : 'var(--yellow)',
    },
  ];

  el.innerHTML = cards.map(c => `
    <div class="quant-signal-card"
      style="border-top:3px solid ${c.color}">
      <div class="quant-card-label">${c.label}</div>
      <div class="quant-card-value"
        style="color:${c.color}">${c.value}</div>
      <div class="quant-card-signal"
        style="background:${c.color}22;color:${c.color}">
        ${c.signal}
      </div>
    </div>`).join('');
}

function renderZScore(z) {
  const el = document.getElementById('quant-zscore');
  if (!el || !z?.current_z === undefined) return;

  // Map z-score to 0-100% for gauge (-3 to +3)
  const pct = Math.min(Math.max(
    ((z.current_z + 3) / 6) * 100, 0), 100
  );
  const col = z.current_z > 1  ? 'var(--red)'
            : z.current_z < -1 ? 'var(--green)'
            : 'var(--yellow)';

  el.innerHTML = `
    <div style="padding:16px">
      <!-- Z-Score Gauge -->
      <div style="text-align:center;margin-bottom:16px">
        <div style="font-size:2.5rem;font-weight:800;
          font-family:monospace;color:${col}">
          ${z.current_z >= 0 ? '+' : ''}${z.current_z}
        </div>
        <div style="font-size:0.85rem;font-weight:700;
          color:${col};margin-top:4px">${z.signal}</div>
      </div>

      <!-- Gauge bar -->
      <div class="zscore-gauge">
        <div class="zscore-needle" style="left:${pct}%"></div>
      </div>
      <div style="display:flex;justify-content:space-between;
        font-size:0.65rem;color:var(--text-dim);margin-bottom:14px">
        <span>Oversold (-3)</span>
        <span>Neutral (0)</span>
        <span>Overbought (+3)</span>
      </div>

      <!-- Stats -->
      ${[
        ['Current Price', '₹' + z.current_price?.toLocaleString('en-IN')],
        ['Rolling Mean',  '₹' + z.rolling_mean?.toLocaleString('en-IN')],
        ['Rolling Std',   '₹' + z.rolling_std?.toLocaleString('en-IN')],
        ['Mean Revert Prob', z.prob_mean_revert + '%'],
        ['Window', z.window + ' periods'],
      ].map(([l, v]) => `
        <div class="quant-row">
          <div class="quant-label">${l}</div>
          <div class="quant-value" style="color:var(--text-pri)">${v}</div>
        </div>`).join('')}

      <!-- Action -->
      <div class="quant-highlight">
        <div class="quant-highlight-label">📌 Recommended Action</div>
        <div class="quant-highlight-value"
          style="color:${col}">${z.action}</div>
      </div>
    </div>`;
}

function renderMomentum(m) {
  const el = document.getElementById('quant-momentum');
  if (!el || !m) return;

  const col = m.composite > 0 ? 'var(--green)'
            : m.composite < 0 ? 'var(--red)'
            : 'var(--text-dim)';

  const periods = [
    ['5 Day ROC',  m.mom_5d],
    ['10 Day ROC', m.mom_10d],
    ['20 Day ROC', m.mom_20d],
    ['30 Day ROC', m.mom_30d],
  ];

  el.innerHTML = `
    <div style="padding:16px">
      <div style="text-align:center;margin-bottom:16px">
        <div style="font-size:2rem;font-weight:800;
          font-family:monospace;color:${col}">
          ${m.composite >= 0 ? '+' : ''}${m.composite}%
        </div>
        <div style="font-size:0.85rem;font-weight:700;
          color:${col};margin-top:4px">${m.signal}</div>
        <div style="font-size:0.78rem;color:var(--text-dim);margin-top:4px">
          Acceleration: <strong style="color:${m.accel_signal==='ACCELERATING'?'var(--green)':'var(--red)'}">
          ${m.accel_signal}</strong>
        </div>
      </div>

      ${periods.map(([label, val]) => {
        if (val === null || val === undefined)
          return '';
        const c   = val >= 0 ? 'var(--green)' : 'var(--red)';
        const pct = Math.min(Math.abs(val) / 10 * 100, 100);
        return `<div class="quant-row">
          <div class="quant-label">${label}</div>
          <div class="quant-bar-wrap">
            <div class="quant-bar"
              style="width:${pct}%;background:${c}"></div>
          </div>
          <div class="quant-value" style="color:${c}">
            ${val >= 0 ? '+' : ''}${val}%
          </div>
        </div>`;
      }).join('')}

      <div class="quant-highlight">
        <div class="quant-highlight-label">📌 Action</div>
        <div class="quant-highlight-value"
          style="color:${col}">${m.action}</div>
      </div>
    </div>`;
}

function renderKelly(k) {
  const el = document.getElementById('quant-kelly');
  if (!el || !k) return;

  const col = k.kelly_half > 10 ? 'var(--green)'
            : k.kelly_half > 0  ? 'var(--yellow)'
            : 'var(--red)';

  el.innerHTML = `
    <div style="padding:16px">
      <!-- Kelly Gauge -->
      <div style="text-align:center;margin-bottom:16px">
        <div style="font-size:2rem;font-weight:800;
          font-family:monospace;color:${col}">
          ${k.kelly_half}%
        </div>
        <div style="font-size:0.82rem;color:var(--text-dim)">
          Recommended Position Size (Half Kelly)
        </div>
        <div style="margin-top:8px">
          <span style="background:${col}22;color:${col};
            padding:3px 12px;border-radius:12px;
            font-size:0.78rem;font-weight:700">
            ${k.risk_level}
          </span>
        </div>
      </div>

      ${[
        ['Win Rate',       k.win_rate + '%'],
        ['Avg Win',        '+' + k.avg_win_pct + '%'],
        ['Avg Loss',       '-' + k.avg_loss_pct + '%'],
        ['Win/Loss Ratio', k.win_loss_ratio + 'x'],
        ['Sharpe Ratio',   k.sharpe_ratio],
        ['Full Kelly',     k.kelly_full + '%'],
        ['Half Kelly',     k.kelly_half + '%'],
        ['Expected Value', k.expected_value + '%/trade'],
        ['Data Points',    k.data_points + ' observations'],
      ].map(([l, v]) => `
        <div class="quant-row">
          <div class="quant-label">${l}</div>
          <div class="quant-value"
            style="color:var(--text-pri)">${v}</div>
        </div>`).join('')}

      <div class="quant-highlight">
        <div class="quant-highlight-label">💡 Position Sizing Advice</div>
        <div class="quant-highlight-value"
          style="color:${col}">${k.advice}</div>
      </div>
    </div>`;
}

function renderDrawdown(d) {
  const el = document.getElementById('quant-drawdown');
  if (!el || !d) return;

  const col  = d.risk_color === 'red'    ? 'var(--red)'
             : d.risk_color === 'orange' ? 'var(--yellow)'
             : d.risk_color === 'yellow' ? '#ffb800'
             : 'var(--green)';

  const ddPct = Math.min(Math.abs(d.current_drawdown_pct) / 30 * 100, 100);

  el.innerHTML = `
    <div style="padding:16px">
      <div style="text-align:center;margin-bottom:16px">
        <div style="font-size:2rem;font-weight:800;
          font-family:monospace;color:${col}">
          ${d.max_drawdown_pct}%
        </div>
        <div style="font-size:0.82rem;color:var(--text-dim)">
          Maximum Drawdown
        </div>
        <div style="margin-top:8px">
          <span style="background:${col}22;color:${col};
            padding:3px 12px;border-radius:12px;
            font-size:0.78rem;font-weight:700">
            ${d.risk_rating}
          </span>
        </div>
      </div>

      <!-- Current DD bar -->
      <div style="margin-bottom:14px">
        <div style="font-size:0.72rem;color:var(--text-dim);
          margin-bottom:4px">Current Drawdown from Peak</div>
        <div style="height:8px;background:var(--bg-base);
          border-radius:4px;overflow:hidden">
          <div style="width:${ddPct}%;height:100%;
            background:${col};border-radius:4px"></div>
        </div>
        <div style="font-size:0.75rem;color:${col};
          margin-top:3px;font-weight:700">
          ${d.current_drawdown_pct}%
        </div>
      </div>

      ${[
        ['Peak Price',    '₹' + d.peak_price?.toLocaleString('en-IN')],
        ['Current Price', '₹' + d.current_price?.toLocaleString('en-IN')],
        ['Recovery Need', d.recovery_needed_pct + '%'],
        ['Avg Drawdown',  d.avg_drawdown_pct + '%'],
        ['🛑 Suggested Stop', '₹' + d.suggested_stop_loss?.toLocaleString('en-IN')],
      ].map(([l, v]) => `
        <div class="quant-row">
          <div class="quant-label">${l}</div>
          <div class="quant-value"
            style="color:${l.includes('Stop')?'var(--red)':'var(--text-pri)'}">
            ${v}
          </div>
        </div>`).join('')}
    </div>`;
}

function renderVolRegime(v) {
  const el = document.getElementById('quant-volregime');
  if (!el || !v) return;

  const col = v.regime_color === 'red'    ? 'var(--red)'
            : v.regime_color === 'green'  ? 'var(--green)'
            : 'var(--yellow)';

  el.innerHTML = `
    <div style="padding:16px">
      <div style="text-align:center;margin-bottom:16px">
        <div style="font-size:1.4rem;font-weight:800;
          color:${col};margin-bottom:8px">${v.regime}</div>
        <div style="font-size:0.82rem;color:var(--text-dim);
          max-width:250px;margin:0 auto;line-height:1.5">
          ${v.strategy}
        </div>
      </div>

      ${[
        ['Current Vol (5d)',   v.current_vol + '%'],
        ['Historical Vol (20d)', v.historical_vol + '%'],
        ['Long-term Vol',     v.long_term_vol + '%'],
        ['Vol Ratio',         v.vol_ratio + 'x'],
        ['Vol Percentile',    v.vol_percentile + '%'],
      ].map(([l, val]) => {
        const pct = Math.min(parseFloat(val) / 60 * 100, 100) || 0;
        return `<div class="quant-row">
          <div class="quant-label">${l}</div>
          <div class="quant-bar-wrap">
            <div class="quant-bar"
              style="width:${pct}%;background:${col}"></div>
          </div>
          <div class="quant-value"
            style="color:var(--text-pri)">${val}</div>
        </div>`;
      }).join('')}

      <div class="quant-highlight">
        <div class="quant-highlight-label">
          Best Strategy in This Regime
        </div>
        <div class="quant-highlight-value" style="color:${col}">
          ${v.best_strategy === 'MEAN_REVERSION'
            ? '🔄 Mean Reversion — fade extremes, buy dips, sell rips'
            : v.best_strategy === 'TREND_FOLLOWING'
            ? '📈 Trend Following — breakout entries, trail stops'
            : '⚖️ Mixed — use both strategies with smaller size'}
        </div>
      </div>
    </div>`;
}

function renderMultiRSI(m) {
  const el = document.getElementById('quant-multirsi');
  if (!el || !m) return;

  const tfLabels = {
    short:  'Short Term',
    medium: 'Medium Term',
    long:   'Long Term',
  };

  const confluenceColor =
    m.confluence.includes('OVERSOLD')   ? 'var(--green)' :
    m.confluence.includes('OVERBOUGHT') ? 'var(--red)'   :
    'var(--yellow)';

  el.innerHTML = `
    <div style="padding:16px">
      <!-- Confluence Signal -->
      <div class="quant-highlight" style="margin-bottom:14px">
        <div class="quant-highlight-label">
          🎯 Multi-TF Confluence Signal
        </div>
        <div class="quant-highlight-value"
          style="color:${confluenceColor};font-weight:700">
          ${m.confluence}
        </div>
      </div>

      <!-- Individual TF RSIs -->
      ${Object.entries(m.timeframes || {}).map(([tf, data]) => {
        const rsi = data.rsi;
        const col = rsi > 70 ? 'var(--red)'
                  : rsi < 30 ? 'var(--green)'
                  : 'var(--text-sec)';
        const pct = rsi;
        return `<div class="quant-row">
          <div class="quant-label">
            ${tfLabels[tf] || tf}
            <div style="font-size:0.7rem;color:var(--text-dim)">
              ${data.window}-period
            </div>
          </div>
          <div style="flex:1;margin:0 12px">
            <!-- RSI Bar -->
            <div style="height:8px;background:linear-gradient(90deg,
              var(--green),var(--yellow),var(--red));
              border-radius:4px;position:relative">
              <div style="position:absolute;top:-3px;
                left:${pct}%;transform:translateX(-50%);
                width:3px;height:14px;background:#fff;
                border-radius:2px"></div>
            </div>
            <div style="display:flex;justify-content:space-between;
              font-size:0.62rem;color:var(--text-dim);margin-top:2px">
              <span>30</span><span>50</span><span>70</span>
            </div>
          </div>
          <div>
            <div style="font-family:monospace;font-weight:700;
              color:${col}">${rsi}</div>
            <div style="font-size:0.7rem;color:${col}">
              ${data.signal}
            </div>
          </div>
        </div>`;
      }).join('')}

      <div class="quant-row" style="border-top:1px solid var(--border);
        margin-top:6px">
        <div class="quant-label" style="font-weight:700">
          Average RSI
        </div>
        <div class="quant-value"
          style="color:var(--accent2);font-size:1.1rem">
          ${m.avg_rsi}
        </div>
      </div>
    </div>`;
}

async function runMonteCarlo() {
  const el   = document.getElementById('quant-montecarlo');
  const days = parseInt(
    document.getElementById('mc-days')?.value || '30'
  );
  if (!el) return;

  el.innerHTML = `
    <div class="ai-loading" style="padding:30px">
      <div class="ai-loading-dot"></div>
      <div class="ai-loading-dot"></div>
      <div class="ai-loading-dot"></div>
      <span>Running 500 simulations...</span>
    </div>`;

  try {
    const res  = await fetch(`${API}/api/quant/monte-carlo`, {
      method:  'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({
        symbol: selectedQuant.symbol,
        days,
        simulations: 500
      })
    });
    const mc = await res.json();

    if (mc.error) {
      el.innerHTML = `<div style="padding:20px;color:var(--red)">${mc.error}</div>`;
      return;
    }

    const upCol   = 'var(--green)';
    const downCol = 'var(--red)';
    const mainCol = mc.prob_up >= 50 ? upCol : downCol;

    el.innerHTML = `
      <div style="padding:16px">
        <!-- Summary -->
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;
          gap:12px;margin-bottom:16px;text-align:center">
          <div style="background:var(--bg-card);border-radius:8px;padding:14px">
            <div style="font-size:0.72rem;color:var(--text-dim);
              margin-bottom:6px">PROB BULLISH</div>
            <div style="font-size:1.8rem;font-weight:800;
              color:${upCol}">${mc.prob_up}%</div>
          </div>
          <div style="background:var(--bg-card);border-radius:8px;padding:14px">
            <div style="font-size:0.72rem;color:var(--text-dim);
              margin-bottom:6px">EXPECTED RETURN</div>
            <div style="font-size:1.8rem;font-weight:800;
              color:${mainCol}">
              ${mc.expected_return >= 0 ? '+' : ''}${mc.expected_return}%
            </div>
          </div>
          <div style="background:var(--bg-card);border-radius:8px;padding:14px">
            <div style="font-size:0.72rem;color:var(--text-dim);
              margin-bottom:6px">PROB BEARISH</div>
            <div style="font-size:1.8rem;font-weight:800;
              color:${downCol}">${mc.prob_down}%</div>
          </div>
        </div>

        <!-- Percentile Distribution -->
        <div style="font-size:0.72rem;font-weight:700;
          color:var(--text-dim);letter-spacing:0.5px;
          margin-bottom:10px">
          PRICE DISTRIBUTION IN ${days} DAYS
        </div>
        <div class="mc-bar-container">
          ${[
            { label:'WORST (5%)',  val:mc.worst_case,            col:'var(--red)'    },
            { label:'BEAR (25%)',  val:mc.percentiles?.p25,      col:'#ff9800'       },
            { label:'MEDIAN',      val:mc.percentiles?.p50,      col:'var(--yellow)' },
            { label:'BULL (75%)',  val:mc.percentiles?.p75,      col:'#8bc34a'       },
            { label:'BEST (95%)',  val:mc.best_case,             col:'var(--green)'  },
          ].map(p => `
            <div class="mc-bar-item">
              <div class="mc-bar-label" style="color:${p.col}">
                ${p.label}
              </div>
              <div class="mc-bar-val" style="color:${p.col}">
                ₹${p.val?.toLocaleString('en-IN',{maximumFractionDigits:0})}
              </div>
              <div style="font-size:0.72rem;color:var(--text-dim);margin-top:2px">
                ${p.val && mc.current_price
                  ? ((p.val - mc.current_price)/mc.current_price*100)
                    .toFixed(1) + '%'
                  : ''}
              </div>
            </div>`).join('')}
        </div>

        <!-- Current Price reference -->
        <div style="text-align:center;font-size:0.8rem;
          color:var(--text-dim);margin-top:8px">
          Current Price: <strong style="color:var(--text-pri)">
          ₹${mc.current_price?.toLocaleString('en-IN')}
          </strong> &nbsp;|&nbsp; ${mc.simulations} Monte Carlo paths over ${mc.days} days
        </div>
      </div>`;

  } catch(e) {
    el.innerHTML = `
      <div style="padding:20px;color:var(--red)">
        Error: ${e.message}
      </div>`;
  }
}

async function loadPairsTrading() {
  const el = document.getElementById('quant-pairs');
  if (!el) return;

  el.innerHTML = `
    <div class="ai-loading" style="padding:20px">
      <div class="ai-loading-dot"></div>
      <div class="ai-loading-dot"></div>
      <div class="ai-loading-dot"></div>
      <span>Scanning for diverged pairs...</span>
    </div>`;

  try {
    const res  = await fetch(`${API}/api/quant/pairs/scan`);
    const json = await res.json();

    if (!json.pairs?.length) {
      el.innerHTML = `
        <div style="padding:20px;color:var(--text-dim)">
          No significant pairs divergence detected currently.
          Need more data — keep scheduler running.
        </div>`;
      return;
    }

    el.innerHTML = `
      <div style="padding:8px 16px;font-size:0.72rem;
        color:var(--text-dim);font-weight:700;letter-spacing:0.5px">
        DIVERGED CORRELATED PAIRS — MEAN REVERSION OPPORTUNITIES
      </div>
      ${json.pairs.map(p => {
        const scol = p.strength === 'STRONG'
          ? 'var(--green)' : 'var(--yellow)';
        return `<div class="pairs-row">
          <div>
            <div style="font-size:0.72rem;color:var(--text-dim)">
              PAIR
            </div>
            <div style="font-weight:700;color:var(--text-pri)">
              ${p.asset_a}
            </div>
            <div style="font-size:0.78rem;color:var(--text-dim)">
              vs ${p.asset_b}
            </div>
          </div>
          <div class="pairs-signal">${p.signal}</div>
          <div>
            <div style="font-size:0.72rem;color:var(--text-dim)">
              Z-SCORE
            </div>
            <div style="font-family:monospace;font-weight:700;
              color:var(--accent)">
              ${p.z_score}
            </div>
          </div>
          <div>
            <span class="pairs-strength
              ${p.strength === 'STRONG'
                ? 'pairs-strong' : 'pairs-moderate'}">
              ${p.strength}
            </span>
            <div style="font-size:0.7rem;color:var(--text-dim);margin-top:3px">
              Corr: ${p.correlation}
            </div>
          </div>
        </div>`;
      }).join('')}`;

  } catch(e) {
    el.innerHTML = `
      <div style="padding:20px;color:var(--red)">
        Error: ${e.message}
      </div>`;
  }
}
// ── Technical Scanner ─────────────────────────────────────────────────────
let techData = null;

async function loadTechnicalScan() {
  const el = document.getElementById('tech-scan-table');
  if (el) el.innerHTML = '<div style="padding:20px;text-align:center;color:var(--text-dim)">⏳ Scanning all assets...</div>';

  try {
    const res  = await fetch(`${API}/api/technical/scan`);
    const json = await res.json();
    renderTechScanTable(json.data || []);
  } catch(e) {
    if (el) el.innerHTML = `<div style="padding:20px;color:var(--red)">Error: ${e.message}</div>`;
  }
}

function renderTechScanTable(data) {
  const el = document.getElementById('tech-scan-table');
  if (!el) return;

  if (!data.length) {
    el.innerHTML = '<div style="padding:20px;color:var(--text-dim)">Not enough data — run scheduler for a few hours.</div>';
    return;
  }

  const typeEmoji = {
    'indian_index':'🇮🇳','global_index':'🌍',
    'commodity':'🛢️','forex':'💱',
    'crypto':'₿','bond':'📈',
  };

  el.innerHTML = `
    <!-- Header -->
    <div class="tech-scan-row" style="border-bottom:2px solid var(--border)">
      <div style="font-size:0.72rem;color:var(--text-dim);font-weight:700">ASSET</div>
      <div style="font-size:0.72rem;color:var(--text-dim);font-weight:700">SCORE</div>
      <div style="font-size:0.72rem;color:var(--text-dim);font-weight:700">VERDICT</div>
      <div style="font-size:0.72rem;color:var(--text-dim);font-weight:700">MACD</div>
      <div style="font-size:0.72rem;color:var(--text-dim);font-weight:700">SUPERTREND</div>
      <div style="font-size:0.72rem;color:var(--text-dim);font-weight:700">KEY SIGNALS</div>
    </div>
    ${data.map(a => {
      const scoreCol =
        a.score >= 70 ? 'var(--green)'  :
        a.score >= 55 ? '#8bc34a'       :
        a.score >= 45 ? 'var(--yellow)' :
        a.score >= 30 ? '#ff9800'       : 'var(--red)';

      const stCol = a.supertrend_trend === 'BULLISH'
        ? 'var(--green)' : 'var(--red)';

      return `<div class="tech-scan-row">
        <div>
          <div style="font-weight:600;color:var(--text-pri)">
            ${typeEmoji[a.asset_type]||'📌'} ${a.name}
          </div>
          <div style="font-size:0.7rem;color:var(--text-dim)">
            ${a.symbol}
          </div>
        </div>
        <div>
          <div style="font-family:monospace;font-weight:800;
            color:${scoreCol};font-size:1.1rem">${a.score}</div>
          <div class="tech-score-bar" style="margin-top:4px">
            <div class="tech-score-fill"
              style="width:${a.score}%;background:${scoreCol}">
            </div>
          </div>
        </div>
        <div>
          <span class="tech-verdict verdict-${a.verdict}">
            ${a.verdict}
          </span>
        </div>
        <div style="font-size:0.78rem;color:var(--text-sec)">
          ${a.macd_signal}
        </div>
        <div style="font-size:0.78rem;font-weight:700;color:${stCol}">
          ${a.supertrend_trend}
        </div>
        <div style="font-size:0.72rem;color:var(--text-dim)">
          ${(a.signals||[]).slice(0,2).join(' | ')}
        </div>
      </div>`;
    }).join('')}`;
}

async function loadTechnicalDetail(symbol, el) {
  // Update active chip
  document.querySelectorAll('.active-chip')
    .forEach(c => c.classList.remove('active-chip'));
  if (el) el.classList.add('active-chip');

  // Show loading
  const banner = document.getElementById('tech-score-banner');
  if (banner) banner.innerHTML = '<div style="color:var(--text-dim)">⏳ Analyzing...</div>';

  try {
    const res  = await fetch(`${API}/api/technical/${encodeURIComponent(symbol)}`);
    const data = await res.json();

    if (data.error) {
      if (banner) banner.innerHTML = `<div style="color:var(--red)">${data.error}</div>`;
      return;
    }

    techData = data;
    renderTechScoreBanner(data.score);
    renderTechMACD(data.macd);
    renderTechBollinger(data.bollinger);
    renderTechSupertrend(data.supertrend);
    renderTechDivergence(data.divergence);
    renderTechStochastic(data.stochastic);
    renderTechATR(data.atr);
    renderTechFibonacci(data.fibonacci);
    renderTechPatterns(data.patterns);
  } catch(e) {
    if (banner) banner.innerHTML = `<div style="color:var(--red)">Error: ${e.message}</div>`;
  }
}

function renderTechScoreBanner(score) {
  const el = document.getElementById('tech-score-banner');
  if (!el || !score) return;

  const col =
    score.score >= 70 ? 'var(--green)'  :
    score.score >= 55 ? '#8bc34a'       :
    score.score >= 45 ? 'var(--yellow)' :
    score.score >= 30 ? '#ff9800'       : 'var(--red)';

  el.innerHTML = `
    <div style="display:flex;align-items:center;gap:20px">
      <div class="tech-score-ring" style="color:${col};border-color:${col}">
        ${score.score}
      </div>
      <div>
        <div style="font-size:1.4rem;font-weight:800;color:${col}">
          ${score.verdict}
        </div>
        <div style="font-size:0.82rem;color:var(--text-dim);margin-top:4px">
          Technical Score: ${score.score}/100
        </div>
        <div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:8px">
          ${(score.signals||[]).map(s => `
            <span style="background:var(--bg-card);border:1px solid var(--border);
              color:var(--text-sec);padding:2px 8px;border-radius:10px;
              font-size:0.72rem">${s}</span>`).join('')}
        </div>
      </div>
    </div>`;
}

function getColor(colorStr) {
  const map = {
    'green':      'var(--green)',
    'lightgreen': '#8bc34a',
    'red':        'var(--red)',
    'orange':     '#ff9800',
    'yellow':     'var(--yellow)',
    'gray':       'var(--text-dim)',
  };
  return map[colorStr] || 'var(--text-sec)';
}

function renderTechMACD(m) {
  const el = document.getElementById('tech-macd');
  if (!el || !m) return;
  const col = getColor(m.color);
  el.innerHTML = `
    <div class="tech-indicator-box">
      <div class="tech-ind-signal" style="color:${col}">
        ${m.signal_str}
      </div>
      <div class="tech-ind-action">${m.action}</div>
      <div style="margin-top:8px">
        ${[
          ['MACD Line',  m.macd],
          ['Signal Line',m.signal],
          ['Histogram',  m.histogram],
        ].map(([l,v]) => `
          <div class="tech-ind-row">
            <span style="color:var(--text-dim)">${l}</span>
            <span style="font-family:monospace;
              color:${v>=0?'var(--green)':'var(--red)'}">
              ${v >= 0 ? '+' : ''}${v}
            </span>
          </div>`).join('')}
      </div>
    </div>`;
}

function renderTechBollinger(b) {
  const el = document.getElementById('tech-bollinger');
  if (!el || !b) return;
  const col  = getColor(b.color);
  const pctB = Math.round(b.pct_b * 100);
  el.innerHTML = `
    <div class="tech-indicator-box">
      <div class="tech-ind-signal" style="color:${col}">
        ${b.signal} ${b.squeeze ? '🔥 SQUEEZE' : ''}
      </div>
      <div class="tech-ind-action">${b.action}</div>
      <div style="margin:8px 0">
        <div style="height:8px;background:linear-gradient(90deg,
          var(--green),var(--yellow),var(--red));
          border-radius:4px;position:relative">
          <div style="position:absolute;top:-3px;left:${pctB}%;
            transform:translateX(-50%);width:3px;height:14px;
            background:#fff;border-radius:2px"></div>
        </div>
        <div style="font-size:0.7rem;color:var(--text-dim);
          margin-top:3px">%B = ${b.pct_b}</div>
      </div>
      ${[
        ['Upper Band', b.upper],
        ['Middle Band',b.middle],
        ['Lower Band', b.lower],
        ['Band Width', b.band_width],
      ].map(([l,v]) => `
        <div class="tech-ind-row">
          <span style="color:var(--text-dim)">${l}</span>
          <span style="font-family:monospace;color:var(--text-pri)">
            ₹${Number(v).toLocaleString('en-IN')}
          </span>
        </div>`).join('')}
    </div>`;
}

function renderTechSupertrend(s) {
  const el = document.getElementById('tech-supertrend');
  if (!el || !s) return;
  const col = s.trend === 'BULLISH' ? 'var(--green)' : 'var(--red)';
  el.innerHTML = `
    <div class="tech-indicator-box" style="border-color:${col}33">
      <div class="tech-ind-signal" style="color:${col}">
        ${s.trend}
      </div>
      <div class="tech-ind-action">${s.action}</div>
      ${[
        ['Supertrend Level', '₹' + s.supertrend?.toLocaleString('en-IN')],
        ['Current Price',    '₹' + s.current_price?.toLocaleString('en-IN')],
        ['Distance',         s.distance_pct + '%'],
        ['🛑 Stop Loss',     '₹' + s.stop_loss?.toLocaleString('en-IN')],
      ].map(([l,v]) => `
        <div class="tech-ind-row">
          <span style="color:var(--text-dim)">${l}</span>
          <span style="font-family:monospace;
            color:${l.includes('Stop')?'var(--red)':'var(--text-pri)'}">
            ${v}
          </span>
        </div>`).join('')}
    </div>`;
}

function renderTechDivergence(d) {
  const el = document.getElementById('tech-divergence');
  if (!el || !d) return;
  el.innerHTML = `
    <div class="tech-indicator-box">
      <div style="font-size:0.78rem;color:var(--text-dim);
        margin-bottom:6px">Current RSI: <strong
        style="color:var(--accent)">${d.current_rsi}</strong>
      </div>
      ${(d.divergences||[]).map(div => {
        const col = getColor(div.color);
        return `
          <div style="background:${col}11;border:1px solid ${col}33;
            border-radius:6px;padding:8px;margin-bottom:6px">
            <div style="font-weight:700;color:${col};font-size:0.8rem">
              ${div.type}
            </div>
            <div style="font-size:0.75rem;color:var(--text-dim);
              margin-top:3px">${div.action}</div>
            <div style="display:flex;justify-content:space-between;
              margin-top:4px">
              <span style="font-size:0.72rem;color:var(--text-dim)">
                Strength: ${div.strength}
              </span>
              <span style="font-size:0.72rem;font-weight:700;
                color:${col}">
                Prob: ${div.prob}%
              </span>
            </div>
          </div>`;
      }).join('')}
    </div>`;
}

function renderTechStochastic(s) {
  const el = document.getElementById('tech-stochastic');
  if (!el || !s) return;
  const col = getColor(s.color);
  el.innerHTML = `
    <div class="tech-indicator-box">
      <div class="tech-ind-signal" style="color:${col}">
        ${s.signal}
      </div>
      <div class="tech-ind-action">${s.action}</div>
      <div style="margin:8px 0">
        <div style="height:8px;background:linear-gradient(90deg,
          var(--green),var(--yellow),var(--red));
          border-radius:4px;position:relative">
          <div style="position:absolute;top:-3px;left:${s.k}%;
            transform:translateX(-50%);width:3px;height:14px;
            background:#fff;border-radius:2px"></div>
        </div>
      </div>
      ${[
        ['%K (Fast)', s.k],
        ['%D (Slow)', s.d],
      ].map(([l,v]) => `
        <div class="tech-ind-row">
          <span style="color:var(--text-dim)">${l}</span>
          <span style="font-family:monospace;color:var(--text-pri)">
            ${v}
          </span>
        </div>`).join('')}
    </div>`;
}

function renderTechATR(a) {
  const el = document.getElementById('tech-atr');
  if (!el || !a) return;
  const volCol =
    a.volatility === 'HIGH'   ? 'var(--red)'    :
    a.volatility === 'NORMAL' ? 'var(--yellow)' : 'var(--green)';
  el.innerHTML = `
    <div class="tech-indicator-box">
      <div class="tech-ind-signal" style="color:${volCol}">
        ${a.volatility} VOLATILITY
      </div>
      <div style="font-size:0.78rem;color:var(--text-dim);margin-bottom:8px">
        ATR: ₹${a.atr} (${a.atr_pct}% of price)
      </div>
      <div style="font-size:0.72rem;font-weight:700;color:var(--red);
        letter-spacing:0.5px;margin-bottom:4px">STOP LOSS LEVELS</div>
      ${Object.entries(a.stop_loss||{}).map(([k,v]) => `
        <div class="tech-ind-row">
          <span style="color:var(--text-dim)">${k}</span>
          <span style="font-family:monospace;color:var(--red)">
            ₹${Number(v).toLocaleString('en-IN')}
          </span>
        </div>`).join('')}
      <div style="font-size:0.72rem;font-weight:700;color:var(--green);
        letter-spacing:0.5px;margin:8px 0 4px">PRICE TARGETS</div>
      ${Object.entries(a.targets||{}).map(([k,v]) => `
        <div class="tech-ind-row">
          <span style="color:var(--text-dim)">${k}</span>
          <span style="font-family:monospace;color:var(--green)">
            ₹${Number(v).toLocaleString('en-IN')}
          </span>
        </div>`).join('')}
    </div>`;
}

function renderTechFibonacci(f) {
  const el = document.getElementById('tech-fibonacci');
  if (!el || !f) return;

  const levelsArr = Object.entries(f.levels || {});
  el.innerHTML = `
    <div class="tech-indicator-box">
      <div style="display:flex;justify-content:space-between;
        margin-bottom:10px;font-size:0.8rem">
        <span style="color:var(--text-dim)">
          Trend: <strong style="color:${f.trend==='UPTREND'?'var(--green)':'var(--red)'}">
          ${f.trend}</strong>
        </span>
        <span style="color:var(--text-dim)">
          Zone: <strong style="color:var(--accent)">${f.fib_zone}</strong>
        </span>
        <span style="color:var(--text-dim)">
          Position: <strong style="color:var(--text-pri)">
          ${f.position_pct}%</strong>
        </span>
      </div>

      <!-- Visual range bar -->
      <div style="position:relative;height:24px;
        background:linear-gradient(90deg,var(--red),var(--yellow),var(--green));
        border-radius:6px;margin-bottom:10px">
        <div style="position:absolute;top:-4px;
          left:${f.position_pct}%;transform:translateX(-50%);
          width:4px;height:32px;background:#fff;
          border-radius:2px;box-shadow:0 0 6px rgba(255,255,255,0.6)">
        </div>
      </div>

      <!-- Fib levels grid -->
      <div class="fib-grid">
        ${levelsArr.map(([name, val]) => {
          const isSup = val <= f.current;
          const isRes = val >  f.current;
          const isNearSup = val === f.nearest_support;
          const isNearRes = val === f.nearest_resistance;
          const col = isNearSup ? 'var(--green)'
                    : isNearRes ? 'var(--red)'
                    : isSup     ? '#8bc34a33'
                    : '#ff456033';
          const textCol = isNearSup ? 'var(--green)'
                        : isNearRes ? 'var(--red)'
                        : 'var(--text-sec)';
          return `<div class="fib-level"
            style="border:1px solid ${isNearSup||isNearRes?col:'var(--border)'}">
            <div class="fib-level-name">${name}</div>
            <div class="fib-level-price" style="color:${textCol}">
              ₹${Number(val).toLocaleString('en-IN')}
            </div>
            ${isNearSup ? '<div style="font-size:0.6rem;color:var(--green)">SUPPORT</div>' : ''}
            ${isNearRes ? '<div style="font-size:0.6rem;color:var(--red)">RESISTANCE</div>' : ''}
          </div>`;
        }).join('')}
      </div>

      <!-- Targets -->
      <div style="font-size:0.72rem;font-weight:700;color:var(--accent);
        letter-spacing:0.5px;margin:8px 0 6px">📈 EXTENSION TARGETS</div>
      ${Object.entries(f.extensions||{}).map(([k,v]) => `
        <div class="tech-ind-row">
          <span style="color:var(--text-dim)">${k}</span>
          <span style="font-family:monospace;color:var(--accent2)">
            ₹${Number(v).toLocaleString('en-IN')}
          </span>
        </div>`).join('')}
    </div>`;
}

function renderTechPatterns(patterns) {
  const el = document.getElementById('tech-patterns');
  if (!el || !patterns) return;

  if (!patterns.length) {
    el.innerHTML = '<div style="color:var(--text-dim);font-size:0.85rem">No significant patterns detected recently.</div>';
    return;
  }

  el.innerHTML = `
    <div style="display:flex;flex-wrap:wrap;gap:8px">
      ${patterns.map(p => {
        const col = p.signal === 'BULLISH' ? 'var(--green)'
                  : p.signal === 'BEARISH' ? 'var(--red)'
                  : 'var(--yellow)';
        return `<div class="pattern-badge"
          style="border-color:${col}44">
          <span style="color:${col};font-weight:700">
            ${p.signal === 'BULLISH' ? '🟢'
              : p.signal === 'BEARISH' ? '🔴' : '🟡'}
          </span>
          <div>
            <div style="font-weight:700;color:${col};font-size:0.8rem">
              ${p.pattern}
            </div>
            <div style="font-size:0.72rem;color:var(--text-dim)">
              ${p.desc}
            </div>
          </div>
        </div>`;
      }).join('')}
    </div>`;
}
init();