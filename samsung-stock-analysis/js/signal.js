/**
 * signal.js — Buy/Sell recommendation model
 * Aggregates scores from all analysis axes with weighted average.
 */

const SIGNAL = (() => {

  // ── Score helpers ─────────────────────────────────────────────────────
  // Each scorer returns a value in [-10, +10]

  function scoreTechnical(indicators) {
    // RSI: oversold(< 30) = +10, overbought(> 70) = -10
    let rsiScore = 0;
    if (indicators.rsi < 30) rsiScore = 10;
    else if (indicators.rsi < 40) rsiScore = 5;
    else if (indicators.rsi < 50) rsiScore = 2;
    else if (indicators.rsi < 60) rsiScore = -2;
    else if (indicators.rsi < 70) rsiScore = -5;
    else rsiScore = -10;

    // MACD: positive histogram = bullish
    const macdScore = indicators.macdHist > 0 ? Math.min(indicators.macdHist / 500, 1) * 10 : Math.max(indicators.macdHist / 500, -1) * 10;

    // Bollinger: near lower band = bullish, near upper = bearish
    const bbRange = indicators.bbUpper - indicators.bbLower;
    const bbPos = (indicators.price - indicators.bbLower) / bbRange; // 0-1
    const bbScore = (0.5 - bbPos) * 10;

    return (rsiScore + macdScore + bbScore) / 3;
  }

  function scoreTrend(indicators) {
    // MA alignment: price > MA5 > MA20 > MA60 > MA120 = very bullish
    let score = 0;
    const p = indicators.price;
    if (p > indicators.ma5) score += 2;
    if (p > indicators.ma20) score += 2;
    if (p > indicators.ma60) score += 3;
    if (p > indicators.ma120) score += 3;
    return score - 5; // center around 0
  }

  function scoreFundamental(fund) {
    let score = 0;
    // PER: <10 = very cheap, 10-15 = fair, >25 = expensive
    if (fund.per < 8) score += 5;
    else if (fund.per < 12) score += 3;
    else if (fund.per < 15) score += 1;
    else if (fund.per < 20) score -= 2;
    else score -= 5;

    // PBR: <1 = very cheap
    if (fund.pbr < 1) score += 5;
    else if (fund.pbr < 1.5) score += 2;
    else if (fund.pbr < 2) score -= 1;
    else score -= 4;

    return Math.max(-10, Math.min(10, score));
  }

  function scoreFinancial(fin) {
    // Check if operating income is trending up in recent quarters
    const recentQ = fin.operatingIncome.slice(-4);
    let trend = 0;
    for (let i = 1; i < recentQ.length; i++) {
      trend += recentQ[i] - recentQ[i - 1];
    }
    const avgTrend = trend / (recentQ.length - 1);
    // Normalize: ±2 trillion won swing = ±10 score
    return Math.max(-10, Math.min(10, (avgTrend / 2) * 10));
  }

  function scoreMacro(macro) {
    let score = 0;
    // Exchange rate: strong USD hurts overseas earnings perception
    if (macro.exchangeRate.value < 1300) score += 3;
    else if (macro.exchangeRate.value < 1400) score += 1;
    else if (macro.exchangeRate.value < 1450) score -= 1;
    else score -= 3;

    // SOX trend
    if (macro.sox.change > 1) score += 3;
    else if (macro.sox.change > 0) score += 1;
    else if (macro.sox.change > -1) score -= 1;
    else score -= 3;

    // Fed rate: lower = better for growth stocks
    if (macro.fedRate.value < 3) score += 2;
    else if (macro.fedRate.value < 4) score += 1;
    else if (macro.fedRate.value < 5) score -= 1;
    else score -= 2;

    // AI server demand
    if (macro.aiServerDemand.value > 7) score += 2;
    else if (macro.aiServerDemand.value > 5) score += 1;
    else score -= 1;

    return Math.max(-10, Math.min(10, score));
  }

  function scoreCommunity(comm) {
    // 0-100 → -10 to +10
    return (comm.overall / 100) * 20 - 10;
  }

  // ── Main compute function ─────────────────────────────────────────────
  function compute(indicators, fund, fin, macro, community) {
    const weights = {
      technical:   0.25,
      trend:       0.15,
      fundamental: 0.20,
      financial:   0.15,
      macro:       0.15,
      community:   0.10,
    };

    const scores = {
      technical:   scoreTechnical(indicators),
      trend:       scoreTrend(indicators),
      fundamental: scoreFundamental(fund),
      financial:   scoreFinancial(fin),
      macro:       scoreMacro(macro),
      community:   scoreCommunity(community),
    };

    let total = 0;
    for (const [key, w] of Object.entries(weights)) {
      total += scores[key] * w;
    }

    let label, color, emoji;
    if (total > 6)       { label = '강력 매수'; color = '#00e676'; emoji = '🚀'; }
    else if (total > 2)  { label = '매수';      color = '#69f0ae'; emoji = '📈'; }
    else if (total > -2) { label = '중립';      color = '#ffd740'; emoji = '⚖️'; }
    else if (total > -6) { label = '매도';      color = '#ff6d00'; emoji = '📉'; }
    else                 { label = '강력 매도'; color = '#f44336'; emoji = '🔻'; }

    return { scores, weights, total, label, color, emoji };
  }

  return { compute };
})();
