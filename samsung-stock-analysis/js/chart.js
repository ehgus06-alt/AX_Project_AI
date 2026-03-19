/**
 * chart.js — Main stock price chart (Candlestick + Line + Volume)
 */

const CHART_MODULE = (() => {
  let priceChart = null;
  let volumeChart = null;
  let allData = [];
  let currentType = 'candlestick';
  let currentPeriod = '3M';

  const periodDays = { '1W': 7, '1M': 30, '3M': 90, '6M': 180, '1Y': 252, '3Y': 756 };

  function filterByPeriod(data, period) {
    const days = periodDays[period] || 90;
    return data.slice(-days);
  }

  function calcMA(data, n) {
    return data.map((_, i) => {
      if (i < n - 1) return null;
      const slice = data.slice(i - n + 1, i + 1);
      return Math.round(slice.reduce((s, d) => s + d.c, 0) / n);
    });
  }

  function render(data) {
    const labels = data.map(d => {
      const dt = new Date(d.t * 1000);
      return dt.toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' });
    });

    const closes = data.map(d => d.c);
    const ma5 = calcMA(data, 5);
    const ma20 = calcMA(data, 20);
    const ma60 = calcMA(data, 60);

    const ctx = document.getElementById('priceChart').getContext('2d');
    const vctx = document.getElementById('volumeChart').getContext('2d');

    if (priceChart) priceChart.destroy();
    if (volumeChart) volumeChart.destroy();

    let priceDataset;
    if (currentType === 'candlestick') {
      priceDataset = {
        type: 'candlestick',
        label: '삼성전자',
        data: data.map(d => ({ x: d.t * 1000, o: d.o, h: d.h, l: d.l, c: d.c })),
        color: { up: '#00e676', down: '#f44336', unchanged: '#ffd740' },
      };
    } else {
      priceDataset = {
        type: 'line',
        label: '종가',
        data: closes,
        borderColor: '#3d91ff',
        backgroundColor: 'rgba(61,145,255,0.08)',
        borderWidth: 2,
        pointRadius: 0,
        fill: true,
        tension: 0.1,
      };
    }

    priceChart = new Chart(ctx, {
      type: currentType === 'candlestick' ? 'candlestick' : 'line',
      data: {
        labels,
        datasets: [
          priceDataset,
          {
            type: 'line', label: 'MA5',
            data: ma5, borderColor: '#ffd740',
            borderWidth: 1.5, pointRadius: 0, tension: 0.1,
          },
          {
            type: 'line', label: 'MA20',
            data: ma20, borderColor: '#ff6b6b',
            borderWidth: 1.5, pointRadius: 0, tension: 0.1,
          },
          {
            type: 'line', label: 'MA60',
            data: ma60, borderColor: '#a78bfa',
            borderWidth: 1.5, pointRadius: 0, tension: 0.1,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: { labels: { color: '#b8c5d1', font: { size: 12 } } },
          tooltip: {
            backgroundColor: 'rgba(16,24,40,0.95)',
            titleColor: '#e8edf2',
            bodyColor: '#b8c5d1',
            borderColor: 'rgba(255,255,255,0.1)',
            borderWidth: 1,
          },
        },
        scales: {
          x: {
            ticks: { color: '#6b7a8d', maxTicksLimit: 10 },
            grid: { color: 'rgba(255,255,255,0.04)' },
          },
          y: {
            position: 'right',
            ticks: {
              color: '#6b7a8d',
              callback: v => v?.toLocaleString('ko-KR') + '원',
            },
            grid: { color: 'rgba(255,255,255,0.06)' },
          },
        },
      },
    });

    // Volume Chart
    const volColors = data.map((d, i) => {
      if (i === 0) return 'rgba(0,230,118,0.5)';
      return d.c >= data[i - 1].c ? 'rgba(0,230,118,0.5)' : 'rgba(244,67,54,0.5)';
    });

    volumeChart = new Chart(vctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          label: '거래량',
          data: data.map(d => d.v),
          backgroundColor: volColors,
          borderWidth: 0,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { display: false }, grid: { display: false } },
          y: {
            position: 'right',
            ticks: {
              color: '#6b7a8d',
              callback: v => (v / 1000000).toFixed(0) + 'M',
            },
            grid: { color: 'rgba(255,255,255,0.03)' },
          },
        },
      },
    });
  }

  async function init() {
    allData = await DATA.getPrices('1y');
    // Filter out any incomplete candles
    allData = allData.filter(d => d.o != null && d.h != null && d.l != null && d.c != null);

    // Fallback to line if financial plugin not available
    if (typeof Chart === 'undefined' || !Chart.registry?.controllers?.candlestick) {
      currentType = 'line';
      const lineBtn = document.getElementById('chartTypeLine');
      const candleBtn = document.getElementById('chartTypeCandle');
      if (lineBtn) lineBtn.classList.add('active');
      if (candleBtn) candleBtn.classList.remove('active');
    }

    renderWithPeriod();
    setupControls();
    updatePriceHeader();
  }

  function renderWithPeriod() {
    render(filterByPeriod(allData, currentPeriod));
  }

  function updatePriceHeader() {
    const last = allData[allData.length - 1];
    const prev = allData[allData.length - 2];
    if (!last) return;
    const change = last.c - prev.c;
    const changePct = (change / prev.c * 100).toFixed(2);
    const isUp = change >= 0;
    document.getElementById('currentPrice').textContent = last.c.toLocaleString('ko-KR') + '원';
    document.getElementById('priceChange').textContent = `${isUp ? '+' : ''}${change.toLocaleString('ko-KR')} (${isUp ? '+' : ''}${changePct}%)`;
    document.getElementById('priceChange').className = 'price-change ' + (isUp ? 'up' : 'down');
    document.getElementById('priceDate').textContent = new Date(last.t * 1000).toLocaleDateString('ko-KR') + ' 기준';
  }

  function setupControls() {
    document.querySelectorAll('.period-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.period-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentPeriod = btn.dataset.period;
        renderWithPeriod();
      });
    });

    document.getElementById('chartTypeLine').addEventListener('click', () => {
      currentType = 'line';
      document.getElementById('chartTypeLine').classList.add('active');
      document.getElementById('chartTypeCandle').classList.remove('active');
      renderWithPeriod();
    });

    document.getElementById('chartTypeCandle').addEventListener('click', () => {
      currentType = 'candlestick';
      document.getElementById('chartTypeCandle').classList.add('active');
      document.getElementById('chartTypeLine').classList.remove('active');
      renderWithPeriod();
    });
  }

  return { init };
})();
