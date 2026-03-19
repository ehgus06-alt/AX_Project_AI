# -*- coding: utf-8 -*-
"""
signal_model.py — 삼성전자 AI 매수/매도 신호 모델 (핵심 모듈)

[역할]
  5개 분석 축의 점수를 받아 최종 매수/매도 신호를 생성합니다.

[모델 구조]
  1단계: 각 분석 축 점수 (TechnicalAnalyzer, FundamentalAnalyzer 등)
  2단계: 설정된 가중치로 가중 평균 산출
  3단계: 신호 강도 조정 (확신도에 따른 가산/감산)
  4단계: 임계값 기반 최종 신호 결정

[신호 범위 해석]
   ≥  6.0  → 🚀 강력매수 (Strong Buy)
   ≥  2.0  → 📈 매수     (Buy)
   ≥ -2.0  → ⚖️  중립    (Neutral)
   ≥ -6.0  → 📉 매도     (Sell)
   <  -6.0  → 🔻 강력매도 (Strong Sell)

[ML 확장]
  - confidence_level() 메서드로 각 축 점수의 표준편차를 계산하여
    신호의 신뢰도(확신도)를 추가로 제공합니다.
  - 향후: 과거 데이터로 학습시킨 RandomForest로 가중치를 동적으로 조정 가능
"""

import json
import numpy as np
import datetime

from config import WEIGHTS, SIGNAL_THRESHOLDS, SIGNAL_LABELS, STOCK_NAME


class SignalModel:
    """
    5개 축 점수 → 최종 매수/매도 신호 변환기.

    사용법:
        model = SignalModel()
        model.set_scores(
            technical   = ta_score,
            fundamental = fa_score,
            financial   = fin_score,
            macro       = ma_score,
            sentiment   = sa_score,
        )
        result = model.predict()
    """

    def __init__(self):
        self.scores: dict = {}
        self.weights: dict = WEIGHTS
        self._last_prediction: dict = {}

    def set_scores(self, technical: float, fundamental: float,
                   financial: float, macro: float, sentiment: float):
        """
        각 분석 축의 점수를 설정합니다.

        Args:
            technical:   기술적 분석 점수 (-10 ~ +10)
            fundamental: 펀더멘탈 분석 점수 (-10 ~ +10)
            financial:   재무건전성 점수 (-10 ~ +10)
            macro:       거시 환경 점수 (-10 ~ +10)
            sentiment:   커뮤니티 감성 점수 (-10 ~ +10)
        """
        self.scores = {
            "technical":   float(technical),
            "fundamental": float(fundamental),
            "financial":   float(financial),
            "macro":       float(macro),
            "sentiment":   float(sentiment),
        }

    def _weighted_score(self) -> float:
        """가중 합산 최종 점수 계산."""
        total = 0.0
        for key, score in self.scores.items():
            weight = self.weights.get(key, 0)
            total += score * weight
        return total

    def _signal_label(self, score: float) -> str:
        """점수 → 매수/매도 레이블 변환."""
        t = SIGNAL_THRESHOLDS
        if   score >= t["strong_buy"]: return "strong_buy"
        elif score >= t["buy"]:        return "buy"
        elif score >= t["neutral"]:    return "neutral"
        elif score >= t["sell"]:       return "sell"
        else:                          return "strong_sell"

    def confidence_level(self) -> float:
        """
        신호 신뢰도 계산 (0~100%).

        모든 축의 점수가 같은 방향(부호)을 가리킬수록 신뢰도가 높아집니다.
        예: 5개 축 모두 양수 → 신뢰도 100%
              절반 양수, 절반 음수 → 신뢰도 낮음

        Returns:
            float — 0~100 (%) 범위
        """
        if not self.scores:
            return 50.0
        vals = list(self.scores.values())
        total  = self._weighted_score()
        # 방향 일치도: 점수와 같은 부호인 축의 가중합 / 전체 가중합
        aligned_weight = sum(
            self.weights.get(k, 0)
            for k, v in self.scores.items()
            if np.sign(v) == np.sign(total) or total == 0
        )
        direction_agreement = aligned_weight   # 이미 합이 1이므로 그대로 %로 사용

        # 절대 점수 크기 (점수가 클수록 확신이 강함)
        magnitude_score = min(abs(total) / 10.0, 1.0)

        confidence = (direction_agreement * 0.5 + magnitude_score * 0.5) * 100
        return round(confidence, 1)

    def predict(self) -> dict:
        """
        최종 매수/매도 예측 결과를 반환합니다.

        Returns:
            dict — {
                "signal":         "strong_buy" | "buy" | "neutral" | "sell" | "strong_sell",
                "label":          "🚀 강력매수" | ... ,
                "total_score":    float,       # -10 ~ +10
                "confidence":     float,       # 0 ~ 100%
                "axis_scores":    dict,        # 각 축 점수
                "axis_weights":   dict,        # 각 축 가중치
                "contributions":  dict,        # 각 축 기여 점수
                "analysis_date":  str,
                "stock":          str,
            }
        """
        # XGBoost 동적 가중치 / 점수 조정
        xgb_prob = None
        xgb_adjustment = 0.0
        try:
            import os
            if os.path.exists("xgboost_model.json"):
                print("    [머신러닝] XGBoost 알고리즘으로 모델 동적 가중치 탐색 중...")
                from ml_optimizer import predict_today
                xgb_prob = predict_today()
                if xgb_prob is not None:
                    # 단기 상승 확률이 매우 높으면(>60%) 기술적/수급 모멘텀 가중치를 일시 극대화
                    if xgb_prob > 0.6:
                        self.weights["technical"] += 0.10
                        self.weights["sentiment"] += 0.05
                        self.weights["fundamental"] -= 0.10
                        self.weights["macro"] -= 0.05
                        xgb_adjustment = +1.5
                    # 하락 확률이 매우 높으면(<40%)
                    elif xgb_prob < 0.4:
                        self.weights["technical"] += 0.10
                        self.weights["sentiment"] += 0.05
                        self.weights["fundamental"] -= 0.10
                        self.weights["macro"] -= 0.05
                        xgb_adjustment = -1.5
                        
                    # 가중치 정규화 (합을 1.0으로)
                    w_sum = sum(self.weights.values())
                    for k in self.weights:
                        self.weights[k] /= w_sum
        except Exception as e:
            print(f"    [경고] XGBoost 최적화 적용 실패: {e}")

        total   = self._weighted_score() + xgb_adjustment
        label   = self._signal_label(total)
        conf    = self.confidence_level()

        # 각 축이 최종 점수에 얼마나 기여했는지
        contributions = {
            k: round(v * self.weights.get(k, 0), 3)
            for k, v in self.scores.items()
        }

        self._last_prediction = {
            "signal":        label,
            "label":         SIGNAL_LABELS.get(label, label),
            "total_score":   round(total, 2),
            "confidence":    conf,
            "xgboost_prob":  round(xgb_prob, 2) if xgb_prob else None,
            "xgboost_adj":   xgb_adjustment,
            "axis_scores":   {k: round(v, 2) for k, v in self.scores.items()},
            "axis_weights":  {k: round(w, 2) for k, w in self.weights.items()},
            "contributions": contributions,
            "analysis_date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "stock":         STOCK_NAME,
        }
        return self._last_prediction

    def to_json(self, filepath: str = "analysis_result.json"):
        """예측 결과를 JSON 파일로 저장합니다."""
        if not self._last_prediction:
            self.predict()
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self._last_prediction, f, ensure_ascii=False, indent=2)
        return filepath


# ──────────────────────────────────────────────────────────────────
# 편의 함수: 4가지 분석 결과를 받아 일괄 처리
# ──────────────────────────────────────────────────────────────────

def run_full_analysis(
    technical_score:   float,
    fundamental_score: float,
    financial_score:   float,
    macro_score:       float,
    sentiment_score:   float,
) -> dict:
    """
    분석 점수 5개를 받아 최종 신호를 반환합니다.
    main.py에서 각 Analyzer 클래스 없이 직접 사용할 때 편리합니다.

    Args:
        technical_score:   기술적 분석 점수
        fundamental_score: 펀더멘탈 점수
        financial_score:   재무건전성 점수
        macro_score:       거시 환경 점수
        sentiment_score:   감성 분석 점수

    Returns:
        dict — predict()와 동일한 구조
    """
    model = SignalModel()
    model.set_scores(
        technical   = technical_score,
        fundamental = fundamental_score,
        financial   = financial_score,
        macro       = macro_score,
        sentiment   = sentiment_score,
    )
    return model.predict()
