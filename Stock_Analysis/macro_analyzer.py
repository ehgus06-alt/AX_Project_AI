# -*- coding: utf-8 -*-
"""
macro_analyzer.py — 거시 환경 분석 모듈

[역할]
  원달러 환율, 미 국채 금리, SOX 반도체 지수, KOSPI, 원유,
  반도체 재고 일수, 중국 PMI 등 거시 지표를 분석하여
  삼성전자 주가에 미치는 영향을 점수화합니다.

[핵심 로직]
  - 삼성전자는 수출 비중이 높아 '고환율 = 유리' (단, 과도한 고환율은 외인 이탈)
  - SOX 지수 상승은 글로벌 반도체 수요 강세를 의미
  - 미 국채 금리 상승은 성장주 밸류에이션 압박
  - 반도체 재고 감소는 수요 회복 신호
"""

import numpy as np
from config import MACRO


class MacroAnalyzer:
    """
    거시 환경 점수 계산 클래스.

    사용법:
        ma = MacroAnalyzer(macro_dict)
        score = ma.score()     # -10 ~ +10
        info  = ma.details()
    """

    def __init__(self, macro_data: dict):
        self.data = macro_data

    # ─────────────────────────────────────────────────────────────
    # 개별 지표 점수 함수
    # ─────────────────────────────────────────────────────────────

    def _score_exchange_rate(self) -> float:
        """
        원달러 환율 점수화.
        삼성전자는 주요 수출 기업이므로 적정 수준의 고환율은 유리합니다.
        그러나 너무 높으면 외국인 투자자 이탈을 유발합니다.

        수익 구간: 1,350~1,500 (이 범위에서 최대 +5점)
        """
        rate  = self.data.get("exchange_rate", 1400)
        trend = self.data.get("exchange_rate_5d", 0)   # 5일 변화

        cfg = MACRO
        # 기본 구간 점수
        if   rate < cfg["exchange_low"]:       base =  -5.0   # 과도한 강원화 → 수출 불리
        elif rate < cfg["exchange_mid_low"]:   base =  -1.0
        elif rate < cfg["exchange_mid_high"]:  base =   5.0   # 적정 고환율 → 수출 유리
        elif rate < cfg["exchange_high"]:      base =   3.0
        else:                                  base =  -3.0   # 과도한 고환율 → 외인 이탈 우려

        # 단기 방향성 가산점
        trend_bonus = 0.0
        if base > 0:
            # 유리한 구간에서 환율 추가 상승 → 소폭 가산
            trend_bonus = np.clip(trend / 50, -1.5, 1.5)
        else:
            # 불리한 구간에서 계속 나빠지면 가산 페널티
            trend_bonus = np.clip(trend / 50, -1.5, 0)

        return max(-10.0, min(10.0, base + trend_bonus))

    def _score_sox(self) -> float:
        """
        SOX (필라델피아 반도체 지수) 5일 변화율 점수화.
        글로벌 반도체 섹터 전반의 투자 심리를 반영합니다.
        """
        pct = self.data.get("sox_5d_change_pct", 0.0)
        cfg = MACRO
        if   pct >= cfg["sox_strong_up"]:   return  9.0
        elif pct >= cfg["sox_up"]:          return  4.0
        elif pct >= cfg["sox_down"]:        return  0.0
        elif pct >= cfg["sox_strong_down"]: return -4.0
        else:                               return -9.0

    def _score_interest_rate(self) -> float:
        """
        미 국채 10년물 금리 점수화.
        금리 상승 → 성장주 할인율 상승 → 주가에 부정적
        """
        yield_ = self.data.get("us10y_yield", 4.0)
        fed    = self.data.get("fed_rate", 4.25)
        cfg    = MACRO

        # 기준금리 대비 국채금리 스프레드
        spread = yield_ - fed
        # 스프레드 확대 = 경기 우려 신호 (음수일수록 좋지 않음)
        spread_score = np.clip(-spread * 4, -3.0, 3.0)

        if   yield_ < cfg["yield_low"]:           base =  6.0
        elif yield_ < cfg["yield_mid"]:           base =  3.0
        elif yield_ < cfg["yield_high"]:          base = -2.0
        else:                                     base = -6.0

        return max(-10.0, min(10.0, base + spread_score))

    def _score_semi_inventory(self) -> float:
        """
        반도체 재고 일수 점수화.
        재고 감소(일수 감소) → 수요 회복 신호 → 긍정적
        삼성전자 반도체 재고: 30~40일 = 건강, 60일 이상 = 과잉 재고
        """
        days = self.data.get("semi_inventory_days", 55)
        if   days < 35:  return  7.0   # 재고 부족 → 수요 강세
        elif days < 45:  return  4.0
        elif days < 55:  return  1.0
        elif days < 65:  return -2.0
        elif days < 80:  return -5.0
        else:            return -8.0   # 심각한 재고 과잉

    def _score_china_pmi(self) -> float:
        """
        중국 제조업 PMI 점수화.
        삼성전자 매출의 약 15%가 중국에서 발생하며,
        중국 경기는 반도체 수요에 직접적 영향을 줍니다.
        """
        pmi = self.data.get("china_pmi", 50.0)
        if   pmi >= 52.0: return  5.0
        elif pmi >= 50.0: return  2.0   # 확장 국면
        elif pmi >= 48.0: return -2.0   # 소폭 수축
        else:             return -5.0   # 수축 국면

    def _score_ai_demand(self) -> float:
        """
        AI 서버 수요 강도 점수화 (/10 스케일).
        HBM/DDR5를 중심으로 AI 데이터센터 수요가 삼성전자 반도체 이익을 견인합니다.
        """
        demand = self.data.get("ai_server_demand", 7.0)
        # /10 스케일을 -10~+10 으로 선형 변환 (5점 = 중립)
        score = (demand - 5.0) * 2.0
        return max(-10.0, min(10.0, score))

    def _score_kospi(self) -> float:
        """KOSPI 5일 변화율 점수화. 시장 전반의 리스크 온/오프를 반영합니다."""
        pct = self.data.get("kospi_5d_change_pct", 0.0)
        if   pct >= 3.0:  return  6.0
        elif pct >= 1.0:  return  3.0
        elif pct >= 0.0:  return  1.0
        elif pct >= -1.0: return -1.0
        elif pct >= -3.0: return -3.0
        else:             return -6.0

    # ─────────────────────────────────────────────────────────────
    # 최종 출력 메서드
    # ─────────────────────────────────────────────────────────────

    def score(self) -> float:
        """
        거시 환경 종합 점수 반환.

        Returns:
            float — -10 ~ +10
        """
        scores = {
            "exchange":   (self._score_exchange_rate(),    0.25),
            "sox":        (self._score_sox(),              0.20),
            "rate":       (self._score_interest_rate(),    0.20),
            "semi_inv":   (self._score_semi_inventory(),   0.15),
            "ai_demand":  (self._score_ai_demand(),        0.10),
            "china_pmi":  (self._score_china_pmi(),        0.05),
            "kospi":      (self._score_kospi(),            0.05),
        }
        total = sum(s * w for s, w in scores.values())
        return round(max(-10.0, min(10.0, total)), 2)

    def details(self) -> dict:
        """거시 환경 지표 상세 정보를 반환합니다."""
        d = self.data
        return {
            "원달러_환율":      f"{d.get('exchange_rate', 'N/A')} KRW/USD",
            "환율_5일변화":     f"{d.get('exchange_rate_5d', 0):+.1f} 원",
            "SOX_현재":         f"{d.get('sox_current', 'N/A')}",
            "SOX_5일변화율":    f"{d.get('sox_5d_change_pct', 0):+.2f}%",
            "미10년물금리":     f"{d.get('us10y_yield', 'N/A')}%",
            "연방기금금리":     f"{d.get('fed_rate', 'N/A')}%",
            "KOSPI_현재":       f"{d.get('kospi_current', 'N/A')}",
            "KOSPI_5일변화율":  f"{d.get('kospi_5d_change_pct', 0):+.2f}%",
            "반도체재고일수":   f"{d.get('semi_inventory_days', 'N/A')}일",
            "AI서버수요":       f"{d.get('ai_server_demand', 'N/A')}/10",
            "중국PMI":          f"{d.get('china_pmi', 'N/A')}",
            "WTI원유":          f"{d.get('wti_oil', 'N/A')} USD/bbl",
            "거시환경_점수":    self.score(),
        }
