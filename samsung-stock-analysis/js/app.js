/**
 * app.js — Main controller: tab routing, initialization pipeline, signal rendering
 */

const APP = (() => {
  const tabs = ['chart', 'technical', 'fundamental', 'macro', 'community', 'news', 'signal'];
  const initialized = new Set();

  async function initTab(tabId) {
    if (initialized.has(tabId)) return;
    initialized.add(tabId);
    try {
      switch (tabId) {
        case 'chart':       await CHART_MODULE.init(); break;
        case 'technical':   await TECHNICAL.init(); break;
        case 'fundamental': FUNDAMENTAL.init(); break;
        case 'macro':       MACRO.init(); break;
        case 'community':   COMMUNITY.init(); break;
        case 'news':        await NEWS_MODULE.init(); break;
        case 'signal':      await initSignalTab(); break;
      }
    } catch (e) {
      console.error(`Tab init error [${tabId}]:`, e);
    }
  }

  async function initSignalTab() {
    const priceData = await DATA.getPrices('1y');
    const slice = priceData.slice(-120);
    const indicators = TECHNICAL.getCurrentIndicators(slice);
    const fund = DATA.getFundamentals();
    const fin = DATA.getFinancials();
    const macro = DATA.getMacro();
    const community = DATA.getCommunity();
    const result = SIGNAL.compute(indicators, fund, fin, macro, community);
    renderSignalResult(result);
  }

  function renderSignalResult(result) {
    const badge = document.getElementById('signalBadge');
    if (badge) {
      badge.textContent = result.emoji + ' ' + result.label;
      badge.style.color = result.color;
      badge.style.borderColor = result.color;
      badge.style.boxShadow = `0 0 30px ${result.color}40`;
    }

    const scoreEl = document.getElementById('signalScore');
    if (scoreEl) { scoreEl.textContent = result.total.toFixed(2); scoreEl.style.color = result.color; }

    const bar = document.getElementById('signalBar');
    if (bar) {
      const pct = ((result.total + 10) / 20) * 100;
      bar.style.width = `${pct}%`;
      bar.style.background = result.color;
    }

    const breakdown = document.getElementById('axisBreakdown');
    if (!breakdown) return;
    const axisLabels = {
      technical:   '📊 기술적 분석 (RSI/MACD/볼린저)',
      trend:       '📈 추세 (이동평균 배열)',
      fundamental: '💰 펀더멘탈 밸류 (PER/PBR)',
      financial:   '📋 재무 건전성 (영업이익)',
      macro:       '🌐 거시적 환경',
      community:   '💬 커뮤니티 감성',
    };
    breakdown.innerHTML = Object.entries(result.scores).map(([key, score]) => {
      const weight = (result.weights[key] * 100).toFixed(0);
      const pct = ((score + 10) / 20) * 100;
      const color = score > 4 ? '#00e676' : score > 0 ? '#69f0ae' : score > -4 ? '#ffd740' : '#f44336';
      const contribution = (score * result.weights[key]).toFixed(2);
      return `
        <div class="axis-row">
          <div class="axis-label">${axisLabels[key]}</div>
          <div class="axis-weight">가중치 ${weight}%</div>
          <div class="axis-bar-wrap">
            <div class="axis-bar-fill" style="width:${pct}%; background:${color}"></div>
          </div>
          <div class="axis-score" style="color:${color}">${score > 0 ? '+' : ''}${score.toFixed(1)}</div>
          <div class="axis-contribution" style="color:${color}">(기여: ${contribution > 0 ? '+' : ''}${contribution})</div>
        </div>`;
    }).join('');

    const rec = document.getElementById('signalRecommendation');
    if (rec) {
      const texts = {
        '강력 매수': '기술적·펀더멘탈·거시 모든 지표가 우호적입니다. 현재 구간은 강력 매수 신호입니다.',
        '매수':      '전반적으로 긍정적인 지표가 우세합니다. 분할 매수 접근이 적합합니다.',
        '중립':      '매수·매도 신호가 혼재합니다. 추가 확인 후 진입하거나 관망 전략이 적합합니다.',
        '매도':      '부정적 지표가 우세합니다. 일부 매도 또는 손절 기준 설정을 권고합니다.',
        '강력 매도': '전반적으로 비우호적인 환경입니다. 보유 물량 정리 및 현금 확보를 권고합니다.',
      };
      rec.textContent = texts[result.label] || '';
    }

    const disc = document.getElementById('signalDisclaimer');
    if (disc) disc.textContent = '⚠️ 본 분석은 참고용이며 투자 판단의 최종 책임은 투자자 본인에게 있습니다. 과거 데이터 기반 모델이며 미래 수익을 보장하지 않습니다.';
  }

  function switchTab(tabId) {
    document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
    const pane = document.getElementById('tab-' + tabId);
    if (pane) pane.classList.add('active');
    const navTab = document.querySelector(`.nav-tab[data-tab="${tabId}"]`);
    if (navTab) navTab.classList.add('active');
    initTab(tabId);
  }

  async function renderHeaderInfo() {
    const quote = await DATA.getQuote();
    const fund = DATA.getFundamentals();
    // Use last data point price from chart for consistency
    const prices = await DATA.getPrices('1y');
    const last = prices[prices.length - 1];
    const prev = prices[prices.length - 2];
    const price = last?.c || quote.price || fund.price;
    const prevClose = prev?.c || quote.prevClose || fund.price;
    const change = price - prevClose;
    const changePct = prevClose > 0 ? ((change / prevClose) * 100).toFixed(2) : '0.00';
    const isUp = change >= 0;

    const el = document.getElementById('stockPriceHeader');
    if (el) {
      el.innerHTML = `
        <span class="header-price">${Math.round(price).toLocaleString('ko-KR')}원</span>
        <span class="header-change ${isUp ? 'up' : 'down'}">
          ${isUp ? '▲' : '▼'} ${Math.abs(Number(changePct))}%
        </span>`;
    }

    const badge = document.getElementById('dataSourceBadge');
    if (badge) {
      badge.textContent = '🟡 모의 데이터';
      badge.title = 'Yahoo Finance CORS 제한으로 현실적 모의 데이터 사용 중';
    }
  }

  function init() {
    renderHeaderInfo();
    document.querySelectorAll('.nav-tab').forEach(tab => {
      tab.addEventListener('click', () => switchTab(tab.dataset.tab));
    });
    switchTab('chart');
    document.body.classList.add('loaded');
  }

  return { init };
})();

document.addEventListener('DOMContentLoaded', () => APP.init());
