/**
 * macro.js — Macro environment analysis module
 */

const MACRO = (() => {
  let exchangeChart = null;

  function renderMacroCards(macro) {
    const cards = [
      { label: '원/달러 환율', value: macro.exchangeRate.value.toLocaleString('ko-KR'), unit: 'KRW/USD', change: macro.exchangeRate.change, tooltip: '환율 상승은 수출기업 실적에 긍정적이나, 외인 자금 이탈 가능성' },
      { label: 'KOSPI', value: macro.kospi.value.toLocaleString('ko-KR'), unit: 'pt', change: macro.kospi.change, tooltip: '국내 증시 전반 흐름' },
      { label: 'SOX (필라델피아 반도체)', value: macro.sox.value.toLocaleString('ko-KR'), unit: 'pt', change: macro.sox.change, tooltip: '글로벌 반도체 섹터 선행지표' },
      { label: '미 10년물 금리', value: macro.us10yYield.value, unit: '%', change: macro.us10yYield.change, tooltip: '금리 하락 시 성장주에 유리' },
      { label: '연방기금금리', value: macro.fedRate.value, unit: '%', change: macro.fedRate.change, tooltip: '미 연준 기준금리' },
      { label: 'WTI 원유', value: macro.wtiOil.value, unit: 'USD/bbl', change: macro.wtiOil.change, tooltip: '제조원가 관련 지표' },
    ];

    const grid = document.getElementById('macroCards');
    if (!grid) return;
    grid.innerHTML = cards.map(c => {
      const isUp = c.change >= 0;
      return `
        <div class="macro-card" title="${c.tooltip}">
          <div class="macro-label">${c.label}</div>
          <div class="macro-value">${c.value} <span class="macro-unit">${c.unit}</span></div>
          <div class="macro-change ${isUp ? 'up' : 'down'}">${isUp ? '▲' : '▼'} ${Math.abs(c.change)}</div>
        </div>`;
    }).join('');

    // Extra indicator cards
    const extras = [
      { label: '반도체 재고', value: macro.semiconductorInventory.value + macro.semiconductorInventory.unit, desc: `재고 추세: ${macro.semiconductorInventory.trend === 'decreasing' ? '감소 중 ✅' : '증가 중 ⚠️'}` },
      { label: 'AI 서버 수요', value: macro.aiServerDemand.value + '/10', desc: '고대역폭 메모리(HBM) 수요 강도' },
      { label: '중국 GDP', value: macro.chinaGdp.value + '%', desc: '최대 시장 경기 지표' },
      { label: 'DXY 달러인덱스', value: macro.dxiIndex.value, desc: '달러 강세 약세 지표' },
    ];

    const extGrid = document.getElementById('macroExtras');
    if (extGrid) {
      extGrid.innerHTML = extras.map(e => `
        <div class="macro-extra-card">
          <div class="macro-label">${e.label}</div>
          <div class="macro-value">${e.value}</div>
          <div class="macro-desc">${e.desc}</div>
        </div>`).join('');
    }
  }

  function renderExchangeTrend(macro) {
    const ctx = document.getElementById('exchangeChart')?.getContext('2d');
    if (!ctx) return;
    if (exchangeChart) exchangeChart.destroy();
    exchangeChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: macro.trend.map(d => d.month),
        datasets: [{
          label: '원/달러 환율',
          data: macro.trend.map(d => d.rate),
          borderColor: '#3d91ff',
          backgroundColor: 'rgba(61,145,255,0.08)',
          borderWidth: 2.5,
          pointRadius: 4,
          pointBackgroundColor: '#3d91ff',
          tension: 0.3,
          fill: true,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { labels: { color: '#b8c5d1' } },
          tooltip: { backgroundColor: 'rgba(16,24,40,0.95)', titleColor: '#e8edf2', bodyColor: '#b8c5d1' },
        },
        scales: {
          x: { ticks: { color: '#6b7a8d' }, grid: { color: 'rgba(255,255,255,0.04)' } },
          y: { position: 'right', ticks: { color: '#6b7a8d', callback: v => v + '원' }, grid: { color: 'rgba(255,255,255,0.06)' } },
        },
      },
    });
  }

  function renderMacroAssessment(macro) {
    const el = document.getElementById('macroAssessment');
    if (!el) return;
    const items = [
      { icon: macro.sox.change > 0 ? '🟢' : '🔴', text: `SOX 지수 ${macro.sox.change > 0 ? '상승' : '하락'} — 반도체 섹터 투자심리 ${macro.sox.change > 0 ? '개선' : '악화'}` },
      { icon: macro.exchangeRate.value < 1400 ? '🟢' : macro.exchangeRate.value < 1450 ? '🟡' : '🔴', text: `원달러 ${macro.exchangeRate.value}원 — ${macro.exchangeRate.value > 1400 ? '고환율 구간, 수출 실적 유리하나 외인 이탈 주의' : '환율 안정화 기대'}` },
      { icon: macro.fedRate.value > 4.5 ? '🔴' : '🟡', text: `연준 기준금리 ${macro.fedRate.value}% — ${macro.fedRate.value > 4.5 ? '고금리 지속, 밸류에이션 압박' : '동결 또는 인하 사이클 진입 기대'}` },
      { icon: '🟢', text: `AI 서버 수요 강도 ${macro.aiServerDemand.value}/10 — HBM 중심 수혜 지속` },
      { icon: macro.semiconductorInventory.trend === 'decreasing' ? '🟢' : '🔴', text: `반도체 재고 ${macro.semiconductorInventory.trend === 'decreasing' ? '감소세 — 가격 반등 기대' : '증가추세 — 가격 압박 지속'}` },
    ];
    el.innerHTML = items.map(i => `<div class="assessment-item">${i.icon} ${i.text}</div>`).join('');
  }

  function init() {
    const macro = DATA.getMacro();
    renderMacroCards(macro);
    renderExchangeTrend(macro);
    renderMacroAssessment(macro);
  }

  return { init };
})();
