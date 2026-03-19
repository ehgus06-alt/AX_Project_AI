# -*- coding: utf-8 -*-
"""
technical_analyzer.py — 기술적 분석 모듈

[역할]
  주가 데이터를 바탕으로 다양한 기술적 지표를 계산하고,
  -10 ~ +10 범위의 점수를 산출합니다.

[포함 지표]
  - RSI (상대강도지수)
  - MACD (이동평균 수렴·발산)
  - 볼린저 밴드
  - 이동평균 배열 (정배열/역배열)
  - 스토캐스틱 오실레이터
  - OBV (On-Balance Volume) 추세

[출력]
  score(): float — -10 ~ +10 (양수: 매수 신호, 음수: 매도 신호)
  details(): dict — 각 지표 값과 해석
"""

import numpy as np
import pandas as pd

from config import TECHNICAL


# ──────────────────────────────────────────────────────────────────
# 지표 계산 유틸리티 함수
# ──────────────────────────────────────────────────────────────────

def calc_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """RSI(상대강도지수) 계산. 0~100 범위."""
    delta = close.diff()
    gain  = delta.clip(lower=0)
    loss  = (-delta).clip(lower=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs  = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)   # NaN → 중립 50


def calc_macd(close: pd.Series,
              fast: int = 12, slow: int = 26, signal: int = 9
             ) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    MACD 계산.

    Returns:
        (macd_line, signal_line, histogram)
    """
    ema_fast    = close.ewm(span=fast,   adjust=False).mean()
    ema_slow    = close.ewm(span=slow,   adjust=False).mean()
    macd_line   = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram   = macd_line - signal_line
    return macd_line, signal_line, histogram


def calc_bollinger(close: pd.Series,
                   period: int = 20, std_mult: float = 2.0
                  ) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    볼린저 밴드 계산.

    Returns:
        (upper, mid, lower)
    """
    mid   = close.rolling(period).mean()
    std   = close.rolling(period).std()
    upper = mid + std_mult * std
    lower = mid - std_mult * std
    return upper, mid, lower


def calc_sma(close: pd.Series, period: int) -> pd.Series:
    """단순이동평균(SMA)."""
    return close.rolling(period).mean()


def calc_stochastic(high: pd.Series, low: pd.Series, close: pd.Series,
                    k_period: int = 14, d_period: int = 3
                   ) -> tuple[pd.Series, pd.Series]:
    """
    스토캐스틱 오실레이터 계산.

    Returns:
        (%K, %D)
    """
    lowest_low   = low.rolling(k_period).min()
    highest_high = high.rolling(k_period).max()
    k = (close - lowest_low) / (highest_high - lowest_low + 1e-9) * 100
    d = k.rolling(d_period).mean()
    return k, d


def calc_obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """OBV(On-Balance Volume) 계산."""
    direction = np.sign(close.diff().fillna(0))
    obv       = (direction * volume).cumsum()
    return obv


# ──────────────────────────────────────────────────────────────────
# 기술적 분석 클래스
# ──────────────────────────────────────────────────────────────────

class TechnicalAnalyzer:
    """
    주가 DataFrame을 입력받아 기술적 분석 점수를 계산합니다.

    사용법:
        ta = TechnicalAnalyzer(price_df)
        score = ta.score()        # -10 ~ +10
        info  = ta.details()      # 각 지표 상세값
    """

    def __init__(self, price_df: pd.DataFrame):
        """
        Args:
            price_df: DataCollector.get_price_data()로 얻은 DataFrame
                      컬럼: [Open, High, Low, Close, Volume]
        """
        self.df     = price_df.copy()
        self.close  = self.df["Close"].astype(float)
        self.high   = self.df["High"].astype(float)
        self.low    = self.df["Low"].astype(float)
        self.volume = self.df["Volume"].astype(float)
        self._computed: dict = {}

    def _compute_all(self):
        """모든 지표를 한 번에 계산합니다."""
        if self._computed:
            return

        cfg = TECHNICAL
        c   = self.close

        # ─ 이동평균 ─
        ma5   = calc_sma(c, cfg["ma_short"])
        ma20  = calc_sma(c, cfg["ma_mid"])
        ma60  = calc_sma(c, cfg["ma_long"])
        ma120 = calc_sma(c, cfg["ma_xlong"])

        # ─ RSI ─
        rsi = calc_rsi(c, cfg["rsi_period"])

        # ─ MACD ─
        macd_line, sig_line, hist = calc_macd(
            c, cfg["macd_fast"], cfg["macd_slow"], cfg["macd_signal"]
        )

        # ─ 볼린저 ─
        bb_upper, bb_mid, bb_lower = calc_bollinger(c, cfg["bb_period"], cfg["bb_std"])

        # ─ 스토캐스틱 ─
        stoch_k, stoch_d = calc_stochastic(
            self.high, self.low, c, cfg["stoch_k"], cfg["stoch_d"]
        )

        # ─ OBV 추세 (20일 EMA와 비교) ─
        obv      = calc_obv(c, self.volume)
        obv_ema  = obv.ewm(span=20, adjust=False).mean()

        # ─ 최신값 추출 ─
        last_close  = float(c.iloc[-1])
        self._computed = {
            "close":      last_close,
            "rsi":        float(rsi.iloc[-1]),
            "macd_hist":  float(hist.iloc[-1]),
            "macd_line":  float(macd_line.iloc[-1]),
            "macd_cross": int(
                (hist.iloc[-1] > 0) and (hist.iloc[-2] <= 0)
                if len(hist) >= 2 else False
            ),  # 골든크로스 여부
            "bb_upper":   float(bb_upper.iloc[-1]) if not pd.isna(bb_upper.iloc[-1]) else last_close * 1.02,
            "bb_lower":   float(bb_lower.iloc[-1]) if not pd.isna(bb_lower.iloc[-1]) else last_close * 0.98,
            "bb_mid":     float(bb_mid.iloc[-1])   if not pd.isna(bb_mid.iloc[-1])   else last_close,
            "bb_position": float(
                (last_close - float(bb_lower.iloc[-1])) /
                max(float(bb_upper.iloc[-1]) - float(bb_lower.iloc[-1]), 1)
            ),  # 0~1 (0: 하단, 1: 상단)
            "stoch_k":    float(stoch_k.iloc[-1]) if not pd.isna(stoch_k.iloc[-1]) else 50.0,
            "stoch_d":    float(stoch_d.iloc[-1]) if not pd.isna(stoch_d.iloc[-1]) else 50.0,
            "ma5":        float(ma5.iloc[-1])   if not pd.isna(ma5.iloc[-1])   else last_close,
            "ma20":       float(ma20.iloc[-1])  if not pd.isna(ma20.iloc[-1])  else last_close,
            "ma60":       float(ma60.iloc[-1])  if not pd.isna(ma60.iloc[-1])  else last_close,
            "ma120":      float(ma120.iloc[-1]) if not pd.isna(ma120.iloc[-1]) else last_close,
            "obv_trend":  int(float(obv.iloc[-1]) > float(obv_ema.iloc[-1])),  # 1: 상승, 0: 하락
        }

    # ─────────────────────────────────────────────────────────────
    # 개별 지표 점수화 (각각 -10 ~ +10)
    # ─────────────────────────────────────────────────────────────

    def _score_rsi(self, rsi: float) -> float:
        """
        RSI 점수화
          < 20 → +10 (극도 과매도)
          < 30 → +7  (과매도)
          < 40 → +3
          50 근처 → 0
          > 60 → -3
          > 70 → -7  (과매수)
          > 80 → -10 (극도 과매수)
        """
        if   rsi < 20: return 10.0
        elif rsi < 30: return 7.0
        elif rsi < 40: return 3.0
        elif rsi < 50: return 1.0
        elif rsi < 60: return -1.0
        elif rsi < 70: return -3.0
        elif rsi < 80: return -7.0
        else:          return -10.0

    def _score_macd(self, hist: float, cross: int, close: float) -> float:
        """
        MACD 히스토그램 + 골든크로스 점수화
        히스토그램을 주가 대비 정규화하여 스케일 독립적 점수 산출
        """
        normalized = (hist / close) * 1000   # 주가 대비 MACD 히스토그램 비율 ‰
        raw_score  = max(-8.0, min(8.0, normalized * 4.0))
        if cross:
            raw_score += 2.0   # 골든크로스 보너스
        return max(-10.0, min(10.0, raw_score))

    def _score_bollinger(self, bb_pos: float) -> float:
        """
        볼린저 위치 점수화
          0~0.1  (하단 이탈) → +10
          0~0.2  (하단 근접) → +6
          0.2~0.35 → +3
          0.35~0.65 (중간) → 0
          0.65~0.8 → -3
          0.8~0.9  (상단 근접) → -6
          0.9~1.0  (상단 이탈) → -10
        """
        if   bb_pos < 0.10: return 10.0
        elif bb_pos < 0.20: return  6.0
        elif bb_pos < 0.35: return  3.0
        elif bb_pos < 0.65: return  0.0
        elif bb_pos < 0.80: return -3.0
        elif bb_pos < 0.90: return -6.0
        else:               return -10.0

    def _score_ma_alignment(self, close: float,
                             ma5: float, ma20: float,
                             ma60: float, ma120: float) -> float:
        """
        이동평균 정배열/역배열 점수화.
        현가 > MA5 > MA20 > MA60 > MA120 → 완전 정배열 (+10)
        현가 < MA5 < MA20 < MA60 < MA120 → 완전 역배열 (-10)
        """
        # 각 조건별 2점 부여
        score = 0.0
        if close > ma5:  score += 2.0
        if close > ma20: score += 2.0
        if close > ma60: score += 3.0
        if close > ma120:score += 3.0
        return score - 5.0   # [0~10] → [-5~+5] 중심 조정

    def _score_stochastic(self, k: float, d: float) -> float:
        """스토캐스틱 점수화. RSI와 유사하되 %K < %D 이탈 주의."""
        diverge_bonus = 0.0
        if k < 20 and k > d:   # 과매도 구간에서 K가 D를 상향돌파 → 반등 신호
            diverge_bonus = 2.0
        if k > 80 and k < d:   # 과매수 구간에서 K가 D를 하향돌파 → 하락 신호
            diverge_bonus = -2.0

        if   k < 20: base =  7.0
        elif k < 30: base =  4.0
        elif k < 45: base =  1.0
        elif k < 55: base =  0.0
        elif k < 70: base = -1.0
        elif k < 80: base = -4.0
        else:        base = -7.0

        return max(-10.0, min(10.0, base + diverge_bonus))

    def _score_obv(self, obv_trend: int) -> float:
        """OBV 추세 점수화. 상승 추세면 +3, 하락이면 -3."""
        return 3.0 if obv_trend else -3.0

    # ─────────────────────────────────────────────────────────────
    # 최종 출력 메서드
    # ─────────────────────────────────────────────────────────────

    def score(self) -> float:
        """
        기술적 분석 종합 점수를 반환합니다.

        Returns:
            float — -10 ~ +10 (양수: 매수, 음수: 매도)
        """
        self._compute_all()
        d = self._computed

        scores = {
            "rsi":          (self._score_rsi(d["rsi"]),          0.25),
            "macd":         (self._score_macd(d["macd_hist"], d["macd_cross"], d["close"]), 0.25),
            "bollinger":    (self._score_bollinger(d["bb_position"]),  0.20),
            "ma_alignment": (self._score_ma_alignment(d["close"], d["ma5"], d["ma20"], d["ma60"], d["ma120"]), 0.20),
            "stochastic":   (self._score_stochastic(d["stoch_k"], d["stoch_d"]), 0.05),
            "obv":          (self._score_obv(d["obv_trend"]),     0.05),
        }
        total = sum(s * w for s, w in scores.values())
        return round(max(-10.0, min(10.0, total)), 2)

    def details(self) -> dict:
        """각 지표의 값과 해석을 담은 딕셔너리를 반환합니다."""
        self._compute_all()
        d = self._computed

        cfg = TECHNICAL

        def interp_rsi(rsi):
            if rsi < cfg["rsi_oversold"]:  return "과매도 (매수 신호)"
            if rsi > cfg["rsi_overbought"]: return "과매수 (매도 신호)"
            return "중립"

        def interp_bb(pos):
            if pos < 0.2: return "하단밴드 근접 (반등 가능성)"
            if pos > 0.8: return "상단밴드 근접 (조정 가능성)"
            return "밴드 내 중립"

        mas = ["ma5", "ma20", "ma60", "ma120"]
        price_above = sum(1 for m in mas if d["close"] > d[m])

        return {
            "현재가":          d["close"],
            "RSI_14":         round(d["rsi"], 1),
            "RSI_해석":        interp_rsi(d["rsi"]),
            "MACD_히스토그램":  round(d["macd_hist"], 0),
            "MACD_골든크로스":  bool(d["macd_cross"]),
            "볼린저_위치":      f"{d['bb_position']*100:.0f}%",
            "볼린저_해석":      interp_bb(d["bb_position"]),
            "이동평균_상위수":  f"{price_above}/4",
            "MA_정배열":        price_above >= 3,
            "스토캐스틱K":     round(d["stoch_k"], 1),
            "OBV_추세":         "상승" if d["obv_trend"] else "하락",
            "기술적_점수":      self.score(),
        }
