/**
 * news.js — News module for Samsung Electronics
 * Fetches via Yahoo Finance, falls back to mock news data
 */

const NEWS_MODULE = (() => {

  function timeAgo(ts) {
    const now = Date.now() / 1000;
    const diff = now - ts;
    if (diff < 3600) return Math.floor(diff / 60) + '분 전';
    if (diff < 86400) return Math.floor(diff / 3600) + '시간 전';
    if (diff < 604800) return Math.floor(diff / 86400) + '일 전';
    return new Date(ts * 1000).toLocaleDateString('ko-KR');
  }

  function getSentimentClass(title) {
    const negKeywords = ['하락', '급락', '손실', '부진', '감소', '위기', '우려', '악화', '하향', '경고', 'drop', 'fall', 'loss', 'cut', 'miss', 'warn'];
    const posKeywords = ['상승', '급등', '호실적', '성장', '증가', '수혜', '반등', '기대', '돌파', 'rise', 'gain', 'beat', 'growth', 'boost', 'surpass'];
    const lc = title.toLowerCase();
    if (negKeywords.some(k => lc.includes(k))) return 'negative';
    if (posKeywords.some(k => lc.includes(k))) return 'positive';
    return 'neutral';
  }

  function renderNews(articles) {
    const container = document.getElementById('newsContainer');
    if (!container) return;

    if (!articles || articles.length === 0) {
      container.innerHTML = '<div style="color:#6b7a8d;text-align:center;padding:40px">뉴스를 불러오는 중...</div>';
      return;
    }

    container.innerHTML = articles.map((a, i) => {
      const sentiment = getSentimentClass(a.title || '');
      const publisher = a.publisher?.name || a.source || '언론사';
      const ts = a.providerPublishTime || a.pubTime || (Date.now() / 1000 - i * 3600);
      const link = a.link || a.url || '#';
      const icon = sentiment === 'positive' ? '📈' : sentiment === 'negative' ? '📉' : '📰';
      return `
        <a class="news-card ${sentiment}" href="${link}" target="_blank" rel="noopener">
          <div class="news-icon">${icon}</div>
          <div class="news-body">
            <div class="news-title">${a.title || '기사 제목 없음'}</div>
            <div class="news-meta">
              <span class="news-publisher">${publisher}</span>
              <span class="news-time">${timeAgo(ts)}</span>
            </div>
          </div>
          <div class="news-arrow">›</div>
        </a>`;
    }).join('');
  }

  function renderSentimentSummary(articles) {
    const pos = articles.filter(a => getSentimentClass(a.title) === 'positive').length;
    const neg = articles.filter(a => getSentimentClass(a.title) === 'negative').length;
    const neu = articles.length - pos - neg;

    const el = document.getElementById('newsSentimentSummary');
    if (!el) return;
    el.innerHTML = `
      <span class="positive">📈 긍정 ${pos}건</span>
      <span class="negative">📉 부정 ${neg}건</span>
      <span style="color:#6b7a8d">⚖️ 중립 ${neu}건</span>
      <span style="color:#6b7a8d;margin-left:auto;font-size:11px">최근 ${articles.length}건 뉴스 분석</span>
    `;
  }

  async function init() {
    const container = document.getElementById('newsContainer');
    if (container) {
      container.innerHTML = '<div style="color:#6b7a8d;text-align:center;padding:40px">📰 뉴스 로딩 중...</div>';
    }
    const news = await DATA.getNews();
    renderNews(news);
    renderSentimentSummary(news);
  }

  return { init };
})();
