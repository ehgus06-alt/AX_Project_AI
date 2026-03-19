/**
 * technical.js — Technical analysis indicators: RSI, MACD, Bollinger Bands, Moving Averages
 */

const TECHNICAL = (() => {
  let chartRSI = null, chartMACD = null, chartBollinger = null;

  // ── Indicator Calculations ────────────────────────────────────────────
  function calcRSI(prices, period = 14) {
    const gains = [], losses = [];
    for (let i = 1; i < prices.length; i++) {
      const d = prices[i] - prices[i - 1];
      gains.push(d > 0 ? d : 0);
      losses.push(d < 0 ? -d : 0);
    }
    const result = new Array(period).fill(null);
    let avgGain = gains.slice(0, period).reduce((a, b) => a + b) / period;
    let avgLoss = losses.slice(0, period).reduce((a, b) => a + b) / period;
    result.push(100 - 100 / (1 + avgGain / (avgLoss || 0.001)));
    for (let i = period; i < gains.length; i++) {
      avgGain = (avgGain * (period - 1) + gains[i]) / period;
      avgLoss = (avgLoss * (period - 1) + losses[i]) / period;
      result.push(100 - 100 / (1 + avgGain / (avgLoss || 0.001)));
    }
    return result;
  }

  function calcEMA(prices, period) {
    const k = 2 / (period + 1);
    const result = [prices[0]];
    for (let i = 1; i < prices.length; i++) {
      result.push(prices[i] * k + result[i - 1] * (1 - k));
    }
    return result;
  }

  function calcMACD(prices) {
    const ema12 = calcEMA(prices, 12);
    const ema26 = calcEMA(prices, 26);
    const macd = ema12.map((v, i) => v - ema26[i]);
    const signal = calcEMA(macd, 9);
    const hist = macd.map((v, i) => v - signal[i]);
    return { macd, signal, hist };
  }

  function calcBollinger(prices, period = 20, mult = 2) {
    return prices.map((_, i) => {
      if (i < period - 1) return { mid: null, upper: null, lower: null };
      const slice = prices.slice(i - period + 1, i + 1);
      const mid = slice.reduce((a, b) => a + b) / period;
      const std = Math.sqrt(slice.reduce((s, v) => s + (v - mid) ** 2, 0) / period);
      return { mid, upper: mid + mult * std, lower: mid - mult * std };
    });
  }

  function calcSMA(prices, n) {
    return prices.map((_, i) => {
      if (i < n - 1) return null;
      return prices.slice(i - n + 1, i + 1).reduce((a, b) => a + b) / n;
    });
  }

  // ── Current Indicator Values for Signal ──────────────────────────────
  function getCurrentIndicators(data) {
    const prices = data.map(d => d.c);
    const rsi = calcRSI(prices);
    const { macd, signal, hist } = calcMACD(prices);
    const bb = calcBollinger(prices);
    const ma5 = calcSMA(prices, 5);
    const ma20 = calcSMA(prices, 20);
    const ma60 = calcSMA(prices, 60);
    const ma120 = calcSMA(prices, 120);
    const last = prices.length - 1;
    const lastBB = bb[last];
    return {
      rsi: rsi[last],
      macdHist: hist[last],
      price: prices[last],
      bbUpper: lastBB?.upper ?? prices[last] * 1.02,
      bbLower: lastBB?.lower ?? prices[last] * 0.98,
      ma5: ma5[last], ma20: ma20[last], ma60: ma60[last], ma120: ma120[last],
    };
  }

  // ── Charts ────────────────────────────────────────────────────────────
  function renderSummaryCards(data) {
    const ind = getCurrentIndicators(data);
    const prices = data.map(d => d.c);
    const { macd, signal, hist } = calcMACD(prices);
    const rsi = calcRSI(prices);
    const last = prices.length - 1;

    const cards = [
      { id: 'rsiCard', label: 'RSI (14)', value: rsi[last]?.toFixed(1), signal: rsi[last] < 30 ? '과매도 🟢' : rsi[last] > 70 ? '과매수 🔴' : '중립 🟡', cls: rsi[last] < 30 ? 'positive' : rsi[last] > 70 ? 'negative' : 'neutral' },
      { id: 'macdCard', label: 'MACD', value: hist[last]?.toFixed(0), signal: hist[last] > 0 ? '상승 동력 🟢' : '하락 동력 🔴', cls: hist[last] > 0 ? 'positive' : 'negative' },
      { id: 'bbCard', label: '볼린저 밴드', value: `${((ind.price - ind.bbLower) / (ind.bbUpper - ind.bbLower) * 100).toFixed(0)}%`, signal: ind.price < ind.bbLower ? '하단 돌파 🟢' : ind.price > ind.bbUpper ? '상단 돌파 🔴' : '밴드 내 🟡', cls: ind.price < ind.bbLower ? 'positive' : ind.price > ind.bbUpper ? 'negative' : 'neutral' },
      { id: 'maCard', label: '이동평균 배열', value: `${[5,20,60,120].filter(n => { const ma = calcSMA(prices, n); return prices[last] > ma[last]; }).length}/4`, signal: prices[last] > (calcSMA(prices,20)[last]||0) ? '정배열 🟢' : '역배열 🔴', cls: prices[last] > (calcSMA(prices,20)[last]||0) ? 'positive' : 'negative' },
    ];

    cards.forEach(c => {
      const el = document.getElementById(c.id);
      if (!el) return;
      el.querySelector('.indicator-value').textContent = c.value;
      const sig = el.querySelector('.indicator-signal');
      sig.textContent = c.signal;
      sig.className = 'indicator-signal ' + c.cls;
    });
  }

  function renderRSI(data) {
    const prices = data.map(d => d.c);
    const rsi = calcRSI(prices);
    const labels = data.map(d => new Date(d.t * 1000).toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' }));
    const ctx = document.getElementById('rsiChart').getContext('2d');
    if (chartRSI) chartRSI.destroy();
    chartRSI = new Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: [
          { label: 'RSI', data: rsi, borderColor: '#a78bfa', borderWidth: 2, pointRadius: 0, tension: 0.1, fill: false },
          { label: '과매수(70)', data: new Array(rsi.length).fill(70), borderColor: 'rgba(244,67,54,0.5)', borderWidth: 1, borderDash: [4,4], pointRadius: 0 },
          { label: '과매도(30)', data: new Array(rsi.length).fill(30), borderColor: 'rgba(0,230,118,0.5)', borderWidth: 1, borderDash: [4,4], pointRadius: 0 },
        ],
      },
      options: chartOpts({ min: 0, max: 100, tickCb: v => v }),
    });
  }

  function renderMACD(data) {
    const prices = data.map(d => d.c);
    const { macd, signal, hist } = calcMACD(prices);
    const labels = data.map(d => new Date(d.t * 1000).toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' }));
    const ctx = document.getElementById('macdChart').getContext('2d');
    if (chartMACD) chartMACD.destroy();
    chartMACD = new Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [
          { type: 'bar', label: '히스토그램', data: hist, backgroundColor: hist.map(v => v >= 0 ? 'rgba(0,230,118,0.5)' : 'rgba(244,67,54,0.5)') },
          { type: 'line', label: 'MACD', data: macd, borderColor: '#3d91ff', borderWidth: 1.5, pointRadius: 0 },
          { type: 'line', label: 'Signal', data: signal, borderColor: '#ffd740', borderWidth: 1.5, pointRadius: 0 },
        ],
      },
      options: chartOpts({ tickCb: v => v?.toFixed(0) }),
    });
  }

  function renderBollinger(data) {
    const prices = data.map(d => d.c);
    const bb = calcBollinger(prices);
    const labels = data.map(d => new Date(d.t * 1000).toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' }));
    const ctx = document.getElementById('bollingerChart').getContext('2d');
    if (chartBollinger) chartBollinger.destroy();
    chartBollinger = new Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: [
          { label: '상단밴드', data: bb.map(b => b.upper), borderColor: 'rgba(244,67,54,0.7)', borderWidth: 1.5, pointRadius: 0, fill: false },
          { label: '중간선', data: bb.map(b => b.mid), borderColor: '#ffd740', borderWidth: 1.5, pointRadius: 0, fill: false },
          { label: '하단밴드', data: bb.map(b => b.lower), borderColor: 'rgba(0,230,118,0.7)', borderWidth: 1.5, pointRadius: 0, fill: false },
          { label: '종가', data: prices, borderColor: '#3d91ff', borderWidth: 2, pointRadius: 0, tension: 0.1, fill: false },
        ],
      },
      options: chartOpts({ tickCb: v => v?.toLocaleString('ko-KR') + '원' }),
    });
  }

  function chartOpts({ min, max, tickCb } = {}) {
    return {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { labels: { color: '#b8c5d1', font: { size: 11 } } },
        tooltip: { backgroundColor: 'rgba(16,24,40,0.95)', titleColor: '#e8edf2', bodyColor: '#b8c5d1', borderColor: 'rgba(255,255,255,0.1)', borderWidth: 1 },
      },
      scales: {
        x: { ticks: { color: '#6b7a8d', maxTicksLimit: 8 }, grid: { color: 'rgba(255,255,255,0.04)' } },
        y: { position: 'right', min, max, ticks: { color: '#6b7a8d', callback: tickCb || (v => v) }, grid: { color: 'rgba(255,255,255,0.06)' } },
      },
    };
  }

  async function init() {
    const data = await DATA.getPrices('1y');
    const slice = data.slice(-90);
    renderSummaryCards(slice);
    renderRSI(slice);
    renderMACD(slice);
    renderBollinger(slice);
  }

  return { init, getCurrentIndicators };
})();
