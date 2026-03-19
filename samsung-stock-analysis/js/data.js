/**
 * data.js — Data layer for Samsung Electronics (005930.KS)
 * Strategy:
 *   1. Real data via CORS proxy → Yahoo Finance public API
 *   2. Fallback to realistic mock data if proxy also fails
 *
 * Current Date assumed: 2026-03-14 (KST)
 */

const DATA = (() => {
  const TICKER = '005930.KS';

  // ── CORS Proxies (tried in order) ─────────────────────────────────────
  const PROXIES = [
    url => `https://corsproxy.io/?${encodeURIComponent(url)}`,
    url => `https://api.allorigins.win/raw?url=${encodeURIComponent(url)}`,
    url => `https://thingproxy.freeboard.io/fetch/${url}`,
  ];

  async function fetchWithProxy(url) {
    for (const makeProxy of PROXIES) {
      try {
        const res = await fetch(makeProxy(url), { signal: AbortSignal.timeout(6000) });
        if (res.ok) return res;
      } catch (_) {}
    }
    throw new Error('All proxies failed for: ' + url);
  }

  // ── Yahoo Finance chart ───────────────────────────────────────────────
  async function fetchYahooChart(period = '1y') {
    const url = `https://query1.finance.yahoo.com/v8/finance/chart/${TICKER}?interval=1d&range=${period}`;
    const res = await fetchWithProxy(url);
    const json = await res.json();
    const r = json.chart.result[0];
    const ts = r.timestamp;
    const q = r.indicators.quote[0];
    return ts.map((t, i) => ({
      t, o: q.open[i], h: q.high[i], l: q.low[i], c: q.close[i], v: q.volume[i],
    })).filter(d => d.c != null && d.o != null);
  }

  // ── Yahoo Finance quote (current price) ───────────────────────────────
  async function fetchYahooQuote() {
    const url = `https://query1.finance.yahoo.com/v8/finance/chart/${TICKER}?interval=1d&range=5d`;
    const res = await fetchWithProxy(url);
    const json = await res.json();
    const r = json.chart.result[0];
    const meta = r.meta;
    return {
      price: meta.regularMarketPrice,
      prevClose: meta.chartPreviousClose || meta.previousClose,
      currency: meta.currency,
      exchange: meta.exchangeName,
    };
  }

  // ── Yahoo Finance News ────────────────────────────────────────────────
  async function fetchYahooNews() {
    const url = `https://query1.finance.yahoo.com/v1/finance/search?q=005930.KS&quotesCount=0&newsCount=10&enableFuzzyQuery=false&newsQueryId=news_cie_vespa`;
    const res = await fetchWithProxy(url);
    const json = await res.json();
    return (json.news || []).slice(0, 8);
  }

  // ── Stale-while-revalidate cache ─────────────────────────────────────
  const _cache = {};
  async function cached(key, fetcher, fallback) {
    if (_cache[key]) return _cache[key];
    try {
      _cache[key] = await fetcher();
      return _cache[key];
    } catch (e) {
      console.warn(`[DATA] ${key} failed, using fallback:`, e.message);
      _cache[key] = fallback();
      return _cache[key];
    }
  }

  // ────────────────────────────────────────────────────────────────────
  //  MOCK DATA (Realistic Samsung Electronics data as of 2026-03-14)
  // ────────────────────────────────────────────────────────────────────
  function generateMockPrices() {
    // Simulate Samsung ~58,000~78,000 range over past year
    const prices = [];
    // Seed: Samsung was around 79k in early 2025, dipped to ~53k in late 2025, recovered
    const anchors = [
      { daysAgo: 252, price: 79400 },
      { daysAgo: 210, price: 68000 },
      { daysAgo: 170, price: 58800 },
      { daysAgo: 130, price: 53200 },
      { daysAgo: 90,  price: 61500 },
      { daysAgo: 50,  price: 56800 },
      { daysAgo: 20,  price: 58900 },
      { daysAgo: 0,   price: 58400 },
    ];

    const now = new Date('2026-03-14');
    // Interpolate
    let anchorIdx = 0;
    let close = anchors[0].price;
    for (let i = 252; i >= 0; i--) {
      const d = new Date(now);
      d.setDate(d.getDate() - i);
      if (d.getDay() === 0 || d.getDay() === 6) continue;

      // Blend toward next anchor
      while (anchorIdx + 1 < anchors.length && i <= anchors[anchorIdx + 1].daysAgo) {
        anchorIdx++;
      }
      const nextAnchor = anchors[Math.min(anchorIdx + 1, anchors.length - 1)];
      const span = anchors[anchorIdx].daysAgo - nextAnchor.daysAgo;
      const t = span > 0 ? (anchors[anchorIdx].daysAgo - i) / span : 1;
      const targetPrice = anchors[anchorIdx].price + (nextAnchor.price - anchors[anchorIdx].price) * Math.min(t, 1);

      // Add noise
      close = close * 0.85 + targetPrice * 0.15 + (Math.random() - 0.5) * 800;
      close = Math.max(50000, Math.min(90000, close));
      const c = Math.round(close / 100) * 100;
      const open = Math.round((c * (1 + (Math.random() - 0.5) * 0.012)) / 100) * 100;
      const high = Math.round((Math.max(open, c) * (1 + Math.random() * 0.012)) / 100) * 100;
      const low  = Math.round((Math.min(open, c) * (1 - Math.random() * 0.012)) / 100) * 100;

      prices.push({
        t: Math.floor(d.getTime() / 1000),
        o: open, h: high, l: low, c: c,
        v: Math.floor(8_000_000 + Math.random() * 22_000_000),
      });
    }
    return prices;
  }

  // ── Public API ────────────────────────────────────────────────────────
  async function getPrices(period = '1y') {
    return cached('prices_' + period, () => fetchYahooChart(period), generateMockPrices);
  }

  async function getQuote() {
    return cached('quote', fetchYahooQuote, () => ({
      price: 58400,
      prevClose: 59100,
      currency: 'KRW',
      exchange: 'KSC',
    }));
  }

  async function getNews() {
    // Always use mock news first — Yahoo Finance search via proxy returns
    // unrelated general tech articles, not Samsung-specific news.
    return getMockNews();
  }

  // ── Fundamentals (Static — 2026-03-14 기준 추정치) ───────────────────
  function getFundamentals() {
    return {
      ticker: '005930',
      name: '삼성전자',
      price: 58400,
      priceChange: -1.2,
      marketCap: 348_000_000_000_000, // 348조
      per: 18.6,
      pbr: 1.08,
      psr: 1.42,
      roe: 6.2,
      eps: 3140,
      dividendYield: 2.9,
      beta: 1.12,
      week52High: 79800,
      week52Low: 52300,
      shares: 5_969_782_550,
      foreignOwnership: 49.8,
      institutionalOwnership: 15.3,
    };
  }

  function getFinancials() {
    return {
      quarters: ['24Q1', '24Q2', '24Q3', '24Q4', '25Q1', '25Q2', '25Q3', '25Q4(E)'],
      revenue:          [71.9, 74.1, 79.1, 75.8, 79.1, 83.2, 80.9, 82.0],
      operatingIncome:  [6.6,  10.4,  9.2,  6.5,  4.2,  7.8,  9.1,  8.8],
      netIncome:        [6.1,   9.8,  8.9,  5.8,  3.9,  7.0,  8.2,  8.0],
      capex:            [9.0,   8.5,  9.2, 10.1,  9.4,  9.8,  9.0,  9.2],
    };
  }

  function getInsiderTrades() {
    return [
      { date: '2026-03-10', name: '국민연금공단',   type: 'buy',  shares: 2_500_000, price: 57800, value: 144_500_000_000 },
      { date: '2026-03-05', name: '이재용 (회장)',   type: 'buy',  shares: 100_000,   price: 56200, value: 5_620_000_000 },
      { date: '2026-02-28', name: '외국계 기관',     type: 'sell', shares: 1_800_000, price: 59400, value: 106_920_000_000 },
      { date: '2026-02-20', name: 'BlackRock',       type: 'buy',  shares: 3_000_000, price: 55100, value: 165_300_000_000 },
      { date: '2026-02-12', name: '국민연금공단',    type: 'sell', shares: 1_000_000, price: 57200, value: 57_200_000_000 },
      { date: '2026-01-31', name: '삼성물산 (특수관계인)', type: 'buy', shares: 200_000, price: 53800, value: 10_760_000_000 },
      { date: '2026-01-15', name: '외국계 기관',     type: 'buy',  shares: 4_000_000, price: 52300, value: 209_200_000_000 },
      { date: '2025-12-20', name: 'Vanguard Group',  type: 'buy',  shares: 2_200_000, price: 54900, value: 120_780_000_000 },
    ];
  }

  // ── Macro ─────────────────────────────────────────────────────────────
  function getMacro() {
    return {
      exchangeRate:     { value: 1462.3, change: +3.5, unit: 'KRW/USD' },
      kospi:            { value: 2467.8, change: -0.8, unit: '' },
      sox:              { value: 4528.1, change: -1.4, unit: '' },
      us10yYield:       { value: 4.44,   change: +0.03, unit: '%' },
      fedRate:          { value: 4.25,   change: 0, unit: '%' },
      wtiOil:           { value: 71.2,   change: +0.4, unit: 'USD/bbl' },
      semiconductorInventory: { value: 58, unit: '일', trend: 'decreasing' },
      dxiIndex:         { value: 104.8, change: +0.3, unit: '' },
      chinaGdp:         { value: 4.8, unit: '%', label: '중국 GDP 성장률' },
      aiServerDemand:   { value: 8.8, unit: '/10', label: 'AI 서버 수요 강도' },
      trend: [
        { month: '25-09', rate: 1342 }, { month: '25-10', rate: 1378 },
        { month: '25-11', rate: 1415 }, { month: '25-12', rate: 1451 },
        { month: '26-01', rate: 1478 }, { month: '26-02', rate: 1468 },
        { month: '26-03', rate: 1462 },
      ],
    };
  }

  // ── Community ─────────────────────────────────────────────────────────
  function getCommunity() {
    return {
      overall: 52,
      platforms: [
        { name: '네이버 종목토론', score: 49, posts: 18420, change: -4 },
        { name: '카카오 오픈채팅', score: 55, posts: 11350, change: +9 },
        { name: '레딧 r/stocks',   score: 48, posts: 4120, change: -6 },
        { name: '인베스팅닷컴',    score: 54, posts: 7800, change: +3 },
        { name: 'X (트위터)',       score: 53, posts: 31500, change: +1 },
      ],
      keywords: [
        { text: 'HBM', weight: 95 }, { text: '반도체', weight: 90 },
        { text: 'AI', weight: 88 }, { text: '실적부진', weight: 75 },
        { text: '배당', weight: 70 }, { text: '외인매도', weight: 68 },
        { text: '환율', weight: 78 }, { text: '파운드리', weight: 65 },
        { text: '목표주가', weight: 60 }, { text: '분할매수', weight: 58 },
        { text: '저점', weight: 72 }, { text: '낸드', weight: 55 },
        { text: '저평가', weight: 65 }, { text: '바닥', weight: 62 },
        { text: 'HBM4', weight: 80 }, { text: '수율', weight: 48 },
      ],
      recentComments: [
        { time: '12분 전', text: 'HBM4 샘플 출하 소식 나왔음. TSMC 위협이 좀 덜해질 수도', sentiment: 'positive' },
        { time: '38분 전', text: '58,000원 아래는 역사적 저PBR 구간, 장기 투자자엔 기회', sentiment: 'positive' },
        { time: '1시간 전', text: '환율 1,460원대... 수출기업엔 나쁘지 않은데 외인 이탈이 문제', sentiment: 'negative' },
        { time: '2시간 전', text: '1분기 실적이 관건. 영업이익 4~5조 나오면 주가 반응 없을수도', sentiment: 'negative' },
        { time: '3시간 전', text: '국민연금 2.5백만주 순매수확인. 바닥 다지는 신호 아닐까', sentiment: 'positive' },
        { time: '4시간 전', text: '목표주가 9만→7만5천 하향 리포트 계속 나오는중', sentiment: 'negative' },
      ],
    };
  }

  // ── Mock News (fallback) ──────────────────────────────────────────────
  function getMockNews() {
    return [
      { title: '삼성전자, HBM4 양산 준비 가속...SK하이닉스와 격차 줄인다', publisher: { name: '한국경제' }, providerPublishTime: Math.floor(Date.now()/1000) - 3600, link: '#' },
      { title: 'Samsung Electronics Q1 2026 operating profit seen at 4.2T won', publisher: { name: 'Reuters' }, providerPublishTime: Math.floor(Date.now()/1000) - 7200, link: '#' },
      { title: '삼성전자 파운드리, 2nm 수율 개선 확인…TSMC 격차 좁힌다', publisher: { name: '조선비즈' }, providerPublishTime: Math.floor(Date.now()/1000) - 10800, link: '#' },
      { title: '외국인, 삼성전자 5거래일 연속 순매도…기관은 매수세 유입', publisher: { name: '매일경제' }, providerPublishTime: Math.floor(Date.now()/1000) - 14400, link: '#' },
      { title: 'Samsung Galaxy S26 series pre-orders beat expectations in China', publisher: { name: 'Bloomberg' }, providerPublishTime: Math.floor(Date.now()/1000) - 21600, link: '#' },
      { title: '삼성전자, AI 온디바이스 반도체 시장 선점 위해 1조 투자 확대', publisher: { name: '전자신문' }, providerPublishTime: Math.floor(Date.now()/1000) - 86400, link: '#' },
      { title: '삼성 주가 52주 신저 근접...바닥론 vs 분할매수 의견 엇갈려', publisher: { name: '서울경제' }, providerPublishTime: Math.floor(Date.now()/1000) - 172800, link: '#' },
      { title: 'Samsung Electronics raises quarterly dividend amid share buyback plan', publisher: { name: 'Yonhap' }, providerPublishTime: Math.floor(Date.now()/1000) - 259200, link: '#' },
    ];
  }

  return {
    getPrices, getQuote, getNews,
    getFundamentals, getFinancials, getInsiderTrades,
    getMacro, getCommunity,
  };
})();
