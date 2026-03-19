/**
 * community.js — Community sentiment analysis module
 */

const COMMUNITY = (() => {

  function renderOverallGauge(score) {
    const el = document.getElementById('sentimentGauge');
    if (!el) return;
    // score 0-100
    const angle = (score / 100) * 180;
    const color = score > 65 ? '#00e676' : score > 40 ? '#ffd740' : '#f44336';
    const label = score > 65 ? '긍정적' : score > 40 ? '중립' : '부정적';
    el.innerHTML = `
      <div class="gauge-container">
        <div class="gauge-arc">
          <svg viewBox="0 0 200 110" xmlns="http://www.w3.org/2000/svg">
            <path d="M 10 100 A 90 90 0 0 1 190 100" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="18" stroke-linecap="round"/>
            <path d="M 10 100 A 90 90 0 0 1 190 100" fill="none" stroke="url(#gaugeGrad)" stroke-width="18" stroke-linecap="round" stroke-dasharray="283" stroke-dashoffset="${283 - (score / 100) * 283}"/>
            <defs>
              <linearGradient id="gaugeGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" style="stop-color:#f44336"/>
                <stop offset="50%" style="stop-color:#ffd740"/>
                <stop offset="100%" style="stop-color:#00e676"/>
              </linearGradient>
            </defs>
            <text x="100" y="95" text-anchor="middle" fill="${color}" font-size="26" font-weight="700">${score}</text>
            <text x="100" y="110" text-anchor="middle" fill="#6b7a8d" font-size="11">${label}</text>
          </svg>
        </div>
        <div class="gauge-labels">
          <span style="color:#f44336">부정</span>
          <span style="color:#ffd740">중립</span>
          <span style="color:#00e676">긍정</span>
        </div>
      </div>`;
  }

  function renderPlatformBars(platforms) {
    const el = document.getElementById('platformSentiment');
    if (!el) return;
    el.innerHTML = platforms.map(p => {
      const color = p.score > 60 ? '#00e676' : p.score > 40 ? '#ffd740' : '#f44336';
      const changeSign = p.change >= 0 ? '+' : '';
      return `
        <div class="platform-row">
          <div class="platform-name">${p.name}</div>
          <div class="platform-bar-wrap">
            <div class="platform-bar" style="width:${p.score}%; background:${color}"></div>
          </div>
          <div class="platform-score" style="color:${color}">${p.score}</div>
          <div class="platform-change ${p.change >= 0 ? 'positive' : 'negative'}">${changeSign}${p.change}</div>
          <div class="platform-posts">${p.posts.toLocaleString()}건</div>
        </div>`;
    }).join('');
  }

  function renderWordCloud(keywords) {
    const el = document.getElementById('wordCloud');
    if (!el) return;
    const max = Math.max(...keywords.map(k => k.weight));
    const sorted = [...keywords].sort(() => Math.random() - 0.5);
    el.innerHTML = sorted.map(k => {
      const size = 12 + (k.weight / max) * 28;
      const opacity = 0.5 + (k.weight / max) * 0.5;
      const colors = ['#3d91ff', '#00e676', '#ffd740', '#a78bfa', '#ff6b6b', '#56d9e3'];
      const color = colors[Math.floor(Math.random() * colors.length)];
      return `<span class="keyword" style="font-size:${size}px; color:${color}; opacity:${opacity}">${k.text}</span>`;
    }).join('');
  }

  function renderRecentComments(comments) {
    const el = document.getElementById('recentComments');
    if (!el) return;
    el.innerHTML = comments.map(c => `
      <div class="comment-item ${c.sentiment}">
        <span class="comment-icon">${c.sentiment === 'positive' ? '📈' : '📉'}</span>
        <div class="comment-body">
          <span class="comment-text">${c.text}</span>
          <span class="comment-time">${c.time}</span>
        </div>
      </div>`).join('');
  }

  function init() {
    const comm = DATA.getCommunity();
    renderOverallGauge(comm.overall);
    renderPlatformBars(comm.platforms);
    renderWordCloud(comm.keywords);
    renderRecentComments(comm.recentComments);
  }

  return { init };
})();
