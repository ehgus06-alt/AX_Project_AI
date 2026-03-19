# -*- coding: utf-8 -*-
"""
sentiment_analyzer.py — 커뮤니티 감성 분석 모듈

[역할]
  뉴스 헤드라인의 긍정/부정 키워드를 분석하여
  시장 참여자들의 감성 점수를 산출합니다.

[분석 방법]
  1. 키워드 매칭 (긍정/부정 단어 카운트)
  2. 강도 가중치 (특정 키워드는 더 강한 신호)
  3. 수급 데이터와의 결합

[확장 가능성]
  - transformers(BERT/KoElectra) 기반 딥러닝 감성 분류로 교체 가능
  - VADER 또는 KR-FinBert 모델 통합 가능
"""

import re
import numpy as np
from config import SENTIMENT


# 강도 가중 키워드 (일반 키워드보다 2~3배 강한 신호)
_STRONG_POSITIVE = {
    "어닝서프라이즈": 3, "급등":  2, "신고가":  2, "매수의견": 2,
    "HBM": 2,  "자사주매입": 2, "배당확대": 2, "목표주가상향": 2,
}
_STRONG_NEGATIVE = {
    "어닝쇼크":  3, "급락":  2, "신저가":  2, "매도의견": 2,
    "영업손실":  3, "목표주가하향": 2, "파운드리수율": 2,
}


class SentimentAnalyzer:
    """
    뉴스 헤드라인 + 수급 데이터로 투자 심리를 분석합니다.

    사용법:
        sa = SentimentAnalyzer(headlines, investor_flow)
        score = sa.score()    # -10 ~ +10
        info  = sa.details()
    """

    def __init__(self, headlines: list[str], investor_flow: dict):
        self.headlines = headlines
        self.flow      = investor_flow
        self._result: dict = {}

    def _analyze_headlines(self) -> dict:
        """헤드라인 딥러닝 분석 (KR-FinBERT). 긍정/부정 확률 및 점수를 반환합니다."""
        if self._result:
            return self._result

        pos_count = 0
        neg_count = 0
        neu_count = 0
        net_score = 0.0

        if self.headlines and len(self.headlines) >= SENTIMENT["min_articles_for_signal"]:
            try:
                from transformers import pipeline
                import torch
                
                device = 0 if torch.cuda.is_available() else -1
                
                # 서울대 금융 특화 언어모델 로드
                classifier = pipeline("sentiment-analysis", model="snunlp/KR-FinBERT-SC", device=device)
                results = classifier(self.headlines)
                
                for idx, res in enumerate(results):
                    label = res['label']
                    score = res['score']
                    
                    if label == 'positive':
                        pos_count += 1
                        net_score += (score * 10)  # 확률에 비례하여 강도 부여
                    elif label == 'negative':
                        neg_count += 1
                        net_score -= (score * 10)
                    else:
                        neu_count += 1

            except ImportError:
                print("    [경고] transformers 패키지가 없습니다. 딥러닝 분석을 생략합니다.")
            except Exception as e:
                print(f"    [경고] KR-FinBERT 실행 오류: {e}")

        total = len(self.headlines)
        self._result = {
            "total_articles":  total,
            "pos_articles":    pos_count,
            "neg_articles":    neg_count,
            "neu_articles":    neu_count,
            "net_score_raw":   net_score,
            "sentiment_ratio": pos_count / total if total > 0 else 0.5,
        }
        return self._result

    def _score_headlines(self) -> float:
        """뉴스 감성 딥러닝 점수화 (-10 ~ +10)."""
        r = self._analyze_headlines()

        if r["total_articles"] < SENTIMENT["min_articles_for_signal"]:
            return 0.0   # 기사 부족 → 중립

        total = r["total_articles"]
        # 기사수 대비 평균 딥러닝 환산 점수
        per_article = r["net_score_raw"] / total
        
        # -10 ~ +10 매핑
        return max(-10.0, min(10.0, per_article * 1.5))

    def _score_flow(self) -> float:
        """
        외국인/기관 5일 수급 점수화.
        방향성(매수/매도)과 크기(금액)를 모두 반영합니다.
        """
        foreign = self.flow.get("foreign_net_5d", 0)
        inst    = self.flow.get("inst_net_5d", 0)

        # 삼성전자 하루 평균 거래대금 약 1조원 기준 정규화
        scale = 1e12  # 1조원 = 10점
        f_score = np.clip(foreign / scale * 8,  -8.0, 8.0)
        i_score = np.clip(inst    / scale * 5,  -5.0, 5.0)

        # 외국인 가중 60%, 기관 40%
        return max(-10.0, min(10.0, f_score * 0.6 + i_score * 0.4))

    def score(self) -> float:
        """
        커뮤니티 감성 + 수급 종합 점수 반환.

        Returns:
            float — -10 ~ +10
        """
        scores = {
            "headlines": (self._score_headlines(), 0.55),
            "flow":      (self._score_flow(),      0.45),
        }
        total = sum(s * w for s, w in scores.values())
        return round(max(-10.0, min(10.0, total)), 2)

    def details(self) -> dict:
        """감성 분석 상세 결과를 반환합니다."""
        r     = self._analyze_headlines()
        total = r["total_articles"]
        return {
            "총_기사수":         total,
            "긍정_기사수":       r["pos_articles"],
            "부정_기사수":       r["neg_articles"],
            "중립_기사수":       r["neu_articles"],
            "긍정_비율":         f"{r['sentiment_ratio']*100:.0f}%" if total > 0 else "N/A",
            "외국인_5일순매수":  f"{self.flow.get('foreign_net_5d', 0)/1e8:.0f}억원",
            "기관_5일순매수":    f"{self.flow.get('inst_net_5d', 0)/1e8:.0f}억원",
            "감성_점수":         self.score(),
        }
