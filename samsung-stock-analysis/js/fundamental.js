/**
 * fundamental.js — Fundamental & financial analysis module
 * Shows PER/PBR/ROE, quarterly financials chart, insider trading table
 */

const FUNDAMENTAL = (() => {
  let finChart = null;

  function renderKeyStats(fund) {
    const stats = [
      { label: 'PER', value: fund.per + '배', note: '업종평균 13.2x', positive: fund.per < 13 },
      { label: 'PBR', value: fund.pbr + '배', note: '장부가 대비', positive: fund.pbr < 1.5 },
      { label: 'ROE', value: fund.roe + '%', note: '자기자본수익률', positive: fund.roe > 10 },
      { label: 'EPS', value: fund.eps.toLocaleString('ko-KR') + '원', note: '주당순이익', positive: true },
      { label: '배당수익률', value: fund.dividendYield + '%', note: '연간 배당', positive: fund.dividendYield > 2 },
      { label: '베타', value: fund.beta, note: '시장 민감도', positive: null },
      { label: '52주 고가', value: fund.week52High.toLocaleString('ko-KR') + '원', note: '', positive: null },
      { label: '52주 저가', value: fund.week52Low.toLocaleString('ko-KR') + '원', note: '', positive: null },
      { label: '시가총액', value: (fund.marketCap / 1e12).toFixed(0) + '조원', note: '', positive: null },
      { label: '외인지분율', value: fund.foreignOwnership + '%', note: '외국인 보유', positive: fund.foreignOwnership > 50 },
      { label: '기관지분율', value: fund.institutionalOwnership + '%', note: '기관 보유', positive: null },
      { label: '발행주식수', value: (fund.shares / 1e8).toFixed(2) + '억주', note: '', positive: null },
    ];

    const grid = document.getElementById('fundKeyStats');
    if (!grid) return;
    grid.innerHTML = stats.map(s => `
      <div class="stat-card">
        <div class="stat-label">${s.label}</div>
        <div class="stat-value ${s.positive === true ? 'positive' : s.positive === false ? 'negative' : ''}">${s.value}</div>
        ${s.note ? `<div class="stat-note">${s.note}</div>` : ''}
      </div>
    `).join('');
  }

  function renderFinancialsChart(fin) {
    const ctx = document.getElementById('financialsChart').getContext('2d');
    if (finChart) finChart.destroy();
    finChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: fin.quarters,
        datasets: [
          {
            type: 'bar',
            label: '매출 (조원)',
            data: fin.revenue,
            backgroundColor: 'rgba(61,145,255,0.6)',
            yAxisID: 'yRevenue',
          },
          {
            type: 'bar',
            label: '영업이익 (조원)',
            data: fin.operatingIncome,
            backgroundColor: 'rgba(0,230,118,0.7)',
            yAxisID: 'yRevenue',
          },
          {
            type: 'line',
            label: '순이익 (조원)',
            data: fin.netIncome,
            borderColor: '#ffd740',
            borderWidth: 2,
            pointRadius: 4,
            tension: 0.2,
            yAxisID: 'yRevenue',
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: { labels: { color: '#b8c5d1' } },
          tooltip: {
            backgroundColor: 'rgba(16,24,40,0.95)',
            titleColor: '#e8edf2',
            bodyColor: '#b8c5d1',
            borderColor: 'rgba(255,255,255,0.1)',
            borderWidth: 1,
          },
        },
        scales: {
          x: { ticks: { color: '#6b7a8d' }, grid: { color: 'rgba(255,255,255,0.04)' } },
          yRevenue: {
            position: 'left',
            ticks: { color: '#6b7a8d', callback: v => v + '조' },
            grid: { color: 'rgba(255,255,255,0.06)' },
          },
        },
      },
    });
  }

  function renderInsiderTable(trades) {
    const tbody = document.getElementById('insiderTableBody');
    if (!tbody) return;
    tbody.innerHTML = trades.map(t => {
      const isBuy = t.type === 'buy';
      const valueStr = (t.value / 1e8).toFixed(0) + '억원';
      return `
        <tr>
          <td>${t.date}</td>
          <td>${t.name}</td>
          <td><span class="trade-badge ${isBuy ? 'buy' : 'sell'}">${isBuy ? '매수' : '매도'}</span></td>
          <td>${t.shares.toLocaleString('ko-KR')}주</td>
          <td>${t.price.toLocaleString('ko-KR')}원</td>
          <td class="${isBuy ? 'positive' : 'negative'}">${valueStr}</td>
        </tr>`;
    }).join('');

    // Summary bar
    const totalBuy = trades.filter(t => t.type === 'buy').reduce((s, t) => s + t.value, 0);
    const totalSell = trades.filter(t => t.type === 'sell').reduce((s, t) => s + t.value, 0);
    const net = totalBuy - totalSell;
    const el = document.getElementById('insiderSummary');
    if (el) {
      el.innerHTML = `
        <span class="positive">매수 ${(totalBuy / 1e8).toFixed(0)}억</span> &nbsp;|&nbsp;
        <span class="negative">매도 ${(totalSell / 1e8).toFixed(0)}억</span> &nbsp;|&nbsp;
        <span class="${net >= 0 ? 'positive' : 'negative'}">순매수 ${(net / 1e8).toFixed(0)}억</span>
      `;
    }
  }

  function init() {
    const fund = DATA.getFundamentals();
    const fin = DATA.getFinancials();
    const trades = DATA.getInsiderTrades();
    renderKeyStats(fund);
    renderFinancialsChart(fin);
    renderInsiderTable(trades);
  }

  return { init };
})();
