# -*- coding: utf-8 -*-
"""
fundamental_analyzer.py — 펀더멘탈 + 재무제표 + 내부자 분석 모듈

[역할]
  valuation(PER/PBR/ROE), 재무건전성(부채비율/FCF),
  영업이익 추세, 내부자 거래 비율을 종합하여 점수를 산출합니다.

[두 가지 서브 점수]
  1. fundamental_score(): 밸류에이션 + 내부자 (가중치 20%)
  2. financial_score():   재무제표 건전성 + 영업이익 추세 (가중치 20%)
"""

import numpy as np
import pandas as pd

from config import FUNDAMENTAL, FINANCIAL


class FundamentalAnalyzer:
    """
    펀더멘탈 분석 클래스 (PER/PBR/ROE, 내부자, 외국인 지분율).

    사용법:
        fa = FundamentalAnalyzer(fundamentals_dict, insider_trades_list, flow_dict)
        score = fa.score()       # -10 ~ +10
        info  = fa.details()
    """

    def __init__(self, fundamentals: dict, insider_trades: list, investor_flow: dict):
        self.fund    = fundamentals
        self.insider = insider_trades
        self.flow    = investor_flow

    # ─────────────────────────────────────────────────────────────
    # 개별 점수 함수
    # ─────────────────────────────────────────────────────────────

    def _score_per(self, per) -> float:
        """PER 점수화 (반도체 업종 평균 ~14배 기준)"""
        if per is None or np.isnan(per) or per <= 0:
            return 0.0   # 정보 없음 → 중립
        cfg = FUNDAMENTAL
        if   per < cfg["per_very_cheap"]:  return 10.0
        elif per < cfg["per_cheap"]:       return  6.0
        elif per < cfg["per_fair"]:        return  3.0
        elif per < cfg["per_expensive"]:   return -2.0
        else:                              return -6.0

    def _score_pbr(self, pbr) -> float:
        """PBR 점수화 (청산가치 대비 주가)"""
        if pbr is None or np.isnan(pbr) or pbr <= 0:
            return 0.0
        cfg = FUNDAMENTAL
        if   pbr < cfg["pbr_very_cheap"]:  return 10.0
        elif pbr < cfg["pbr_cheap"]:       return  6.0
        elif pbr < cfg["pbr_fair"]:        return  2.0
        elif pbr < cfg["pbr_expensive"]:   return -3.0
        else:                              return -7.0

    def _score_roe(self, roe) -> float:
        """ROE 점수화 — yfinance는 소수점(0.1=10%) 반환"""
        if roe is None or np.isnan(roe):
            return 0.0
        # 소수 형태로 넘어오는 경우 비율 변환
        roe_pct = roe * 100 if abs(roe) < 1 else roe
        cfg = FUNDAMENTAL
        if   roe_pct >= cfg["roe_excellent"]: return  8.0
        elif roe_pct >= cfg["roe_good"]:      return  4.0
        elif roe_pct >= cfg["roe_fair"]:      return  1.0
        elif roe_pct >= 0:                    return -3.0
        else:                                 return -8.0   # ROE 음수 = 순손실

    def _score_dividend(self, dy) -> float:
        """배당수익률 점수화 (방어주 특성)"""
        if dy is None or np.isnan(dy):
            return 0.0
        dy_pct = dy * 100 if abs(dy) < 1 else dy
        if   dy_pct >= 4.0: return  4.0
        elif dy_pct >= 2.5: return  2.0
        elif dy_pct >= 1.0: return  0.0
        else:               return -1.0

    def _score_insider(self, trades: list) -> float:
        """
        내부자 순매수 비율로 점수를 산출합니다.
        금액 기준 (단순 건수 아님)으로 계산하여 대형 거래를 반영합니다.
        """
        if not trades:
            return 0.0
        total_buy  = sum(t["value"] for t in trades if t["type"] == "buy")
        total_sell = sum(t["value"] for t in trades if t["type"] == "sell")
        total      = total_buy + total_sell
        if total == 0:
            return 0.0

        buy_ratio = total_buy / total
        cfg = FUNDAMENTAL
        if   buy_ratio >= cfg["insider_bullish"]: return  6.0
        elif buy_ratio >= 0.5:                    return  2.0
        elif buy_ratio >= cfg["insider_bearish"]: return  0.0
        else:                                     return -5.0

    def _score_flow(self, flow: dict) -> float:
        """
        외국인/기관 5일 순매수 점수화.
        삼성전자 시총 대비 비율로 정규화합니다.
        """
        market_cap = self.fund.get("market_cap", 350e12)
        if market_cap == 0:
            market_cap = 350e12

        foreign = flow.get("foreign_net_5d", 0) / market_cap * 10000  # bps 단위
        inst    = flow.get("inst_net_5d", 0) / market_cap * 10000

        # 외국인 가중 70%, 기관 30%
        combined = foreign * 0.7 + inst * 0.3
        # 0.01 bps ≈ ±1 점
        return max(-8.0, min(8.0, combined * 100))

    def score(self) -> float:
        """
        펀더멘탈 종합 점수 반환.

        Returns:
            float — -10 ~ +10
        """
        f = self.fund
        scores = {
            "per":      (self._score_per(f.get("per")),           0.30),
            "pbr":      (self._score_pbr(f.get("pbr")),           0.25),
            "roe":      (self._score_roe(f.get("roe")),           0.20),
            "dividend": (self._score_dividend(f.get("dividend_yield")), 0.10),
            "insider":  (self._score_insider(self.insider),       0.10),
            "flow":     (self._score_flow(self.flow),             0.05),
        }
        total = sum(s * w for s, w in scores.values())
        return round(max(-10.0, min(10.0, total)), 2)

    def details(self) -> dict:
        """각 지표값과 해석을 반환합니다."""
        f         = self.fund
        per       = f.get("per", float("nan"))
        pbr       = f.get("pbr", float("nan"))
        roe       = f.get("roe", float("nan"))
        roe_pct   = roe * 100 if isinstance(roe, float) and abs(roe) < 1 else roe
        dy        = f.get("dividend_yield", float("nan"))
        dy_pct    = dy * 100 if isinstance(dy, float) and abs(dy) < 1 else dy

        total_buy  = sum(t["value"] for t in self.insider if t["type"] == "buy")
        total_sell = sum(t["value"] for t in self.insider if t["type"] == "sell")

        return {
            "현재가":           f.get("current_price", "N/A"),
            "시가총액":          f"{f.get('market_cap', 0)/1e12:.0f}조원" if f.get('market_cap') else "N/A",
            "PER":              round(per, 1) if not np.isnan(per) else "N/A",
            "PBR":              round(pbr, 2) if not np.isnan(pbr) else "N/A",
            "ROE":              f"{roe_pct:.1f}%" if isinstance(roe_pct, float) and not np.isnan(roe_pct) else "N/A",
            "배당수익률":        f"{dy_pct:.1f}%" if isinstance(dy_pct, float) and not np.isnan(dy_pct) else "N/A",
            "52주_고가":        f.get("week_52_high", "N/A"),
            "52주_저가":        f.get("week_52_low", "N/A"),
            "내부자_매수금액":   f"{total_buy/1e8:.0f}억원",
            "내부자_매도금액":   f"{total_sell/1e8:.0f}억원",
            "내부자_순매수비율": f"{total_buy/(total_buy+total_sell)*100:.0f}%" if (total_buy+total_sell) > 0 else "N/A",
            "펀더멘탈_점수":     self.score(),
        }


class FinancialAnalyzer:
    """
    재무제표 기반 건전성 점수 산출 클래스.

    사용법:
        fin = FinancialAnalyzer(income_df, balance_df, cashflow_df)
        score = fin.score()     # -10 ~ +10
        info  = fin.details()
    """

    def __init__(self, income_df: pd.DataFrame,
                 balance_df: pd.DataFrame,
                 cashflow_df: pd.DataFrame):
        self.income   = income_df
        self.balance  = balance_df
        self.cashflow = cashflow_df

    # ─────────────────────────────────────────────────────────────
    # 영업이익 추세 점수
    # ─────────────────────────────────────────────────────────────

    def _score_op_trend(self) -> float:
        """
        최근 4분기 영업이익의 QoQ 평균 성장률로 점수를 산출합니다.
        단순 평균이 아닌 가중 평균(최신 분기에 더 높은 가중치)을 사용합니다.
        """
        col = "operating_income"
        if col not in self.income.columns or len(self.income) < 2:
            return 0.0

        recent = self.income[col].dropna().tail(4)
        if len(recent) < 2:
            return 0.0

        # QoQ 성장률 계산
        qoq_pct = recent.pct_change().dropna() * 100  # %
        # 최신일수록 가중치 높게 (1, 2, 3 등비 가중)
        weights = np.array([1, 2, 3])[:len(qoq_pct)]
        weights = weights / weights.sum()
        avg_growth = float(np.dot(qoq_pct.values, weights[-len(qoq_pct):]))

        cfg = FINANCIAL
        if   avg_growth >= cfg["op_growth_excellent"]: return 10.0
        elif avg_growth >= cfg["op_growth_good"]:      return  5.0
        elif avg_growth >= 0:                           return  1.0
        elif avg_growth >= cfg["op_growth_bad"]:       return -3.0
        elif avg_growth >= cfg["op_growth_terrible"]:  return -6.0
        else:                                           return -10.0

    def _score_revenue_trend(self) -> float:
        """매출 YoY 성장률 점수화."""
        col = "revenue"
        if col not in self.income.columns or len(self.income) < 5:
            return 0.0
        try:
            yoy = float(
                (self.income[col].iloc[-1] - self.income[col].iloc[-5])
                / abs(self.income[col].iloc[-5]) * 100
            )
            if   yoy >= 20: return 8.0
            elif yoy >= 10: return 5.0
            elif yoy >=  0: return 1.0
            elif yoy >= -5: return -2.0
            elif yoy >= -15: return -5.0
            else:            return -8.0
        except Exception:
            return 0.0

    def _score_debt_ratio(self) -> float:
        """부채비율 점수화."""
        if ("total_liabilities" not in self.balance.columns or
                "equity" not in self.balance.columns):
            return 0.0
        try:
            liab   = float(self.balance["total_liabilities"].iloc[-1])
            equity = float(self.balance["equity"].iloc[-1])
            ratio  = (liab / equity * 100) if equity > 0 else 200
            cfg    = FINANCIAL
            if   ratio < cfg["debt_ratio_safe"]:    return 6.0
            elif ratio < cfg["debt_ratio_warning"]: return 3.0
            elif ratio < cfg["debt_ratio_danger"]:  return -2.0
            else:                                   return -7.0
        except Exception:
            return 0.0

    def _score_fcf(self) -> float:
        """잉여현금흐름(FCF) 점수화."""
        if "fcf" not in self.cashflow.columns:
            return 0.0
        try:
            recent_fcf = self.cashflow["fcf"].dropna().tail(2)
            if len(recent_fcf) == 0:
                return 0.0
            avg_fcf = float(recent_fcf.mean())
            if avg_fcf > 5e12:   return FINANCIAL["fcf_positive_bonus"] + 2
            if avg_fcf > 0:      return FINANCIAL["fcf_positive_bonus"]
            if avg_fcf > -3e12:  return FINANCIAL["fcf_negative_penalty"] + 1
            return FINANCIAL["fcf_negative_penalty"]
        except Exception:
            return 0.0

    def _score_op_margin(self) -> float:
        """영업이익률 점수화."""
        if ("operating_income" not in self.income.columns or
                "revenue" not in self.income.columns):
            return 0.0
        try:
            op  = float(self.income["operating_income"].dropna().iloc[-1])
            rev = float(self.income["revenue"].dropna().iloc[-1])
            margin = op / rev * 100 if rev > 0 else 0.0
            if   margin >= 20: return 10.0
            elif margin >= 15: return  7.0
            elif margin >= 10: return  4.0
            elif margin >=  5: return  1.0
            elif margin >=  0: return -2.0
            else:              return -7.0
        except Exception:
            return 0.0

    def score(self) -> float:
        """
        재무제표 건전성 종합 점수 반환.

        Returns:
            float — -10 ~ +10
        """
        scores = {
            "op_trend":    (self._score_op_trend(),       0.35),
            "revenue":     (self._score_revenue_trend(),  0.20),
            "debt":        (self._score_debt_ratio(),     0.20),
            "fcf":         (self._score_fcf(),            0.15),
            "op_margin":   (self._score_op_margin(),      0.10),
        }
        total = sum(s * w for s, w in scores.values())
        return round(max(-10.0, min(10.0, total)), 2)

    def details(self) -> dict:
        """재무제표 주요 지표를 요약합니다."""
        result = {}
        try:
            if "operating_income" in self.income.columns:
                recent = self.income["operating_income"].dropna().tail(4)
                result["최근영업이익(조)"] = [round(x/1e12, 2) for x in recent.values]
            if "revenue" in self.income.columns:
                result["최근매출(조)"] = [round(x/1e12, 1) for x in self.income["revenue"].dropna().tail(4).values]
            if "fcf" in self.cashflow.columns:
                result["최근FCF(조)"] = [round(x/1e12, 2) for x in self.cashflow["fcf"].dropna().tail(4).values]
            if "total_liabilities" in self.balance.columns and "equity" in self.balance.columns:
                liab = float(self.balance["total_liabilities"].iloc[-1])
                eq   = float(self.balance["equity"].iloc[-1])
                result["부채비율"] = f"{liab/eq*100:.0f}%"
        except Exception:
            pass
        result["재무건전성_점수"] = self.score()
        return result
