# -*- coding: utf-8 -*-
"""
main.py — 삼성전자 AI 주식 분석 모델 실행 진입점

[실행 방법]
  python main.py                  # 기본 실행 (콘솔 출력)
  python main.py --json           # JSON 파일로도 저장
  python main.py --verbose        # 모든 세부 지표 출력
  python main.py --mock           # 실제 API 없이 모의 데이터로만 실행 (테스트)

[전체 분석 파이프라인]
  DataCollector → 5종 Analyzer → SignalModel → 결과 출력
"""

import sys
import json
import argparse
import datetime

try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init(autoreset=True)
    _COLOR = True
except ImportError:
    _COLOR = False

# ── 색상 출력 헬퍼 ──────────────────────────────────────────────
def _c(text: str, color: str = "") -> str:
    if not _COLOR:
        return text
    colors = {
        "green":  Fore.GREEN, "red":    Fore.RED,  "yellow": Fore.YELLOW,
        "cyan":   Fore.CYAN,  "white":  Fore.WHITE, "blue":  Fore.BLUE,
        "bold":   Style.BRIGHT,
    }
    return f"{colors.get(color, '')}{text}{Style.RESET_ALL}"


def print_header():
    border = "═" * 60
    print(_c(f"\n{border}", "cyan"))
    print(_c("  🤖 삼성전자 (005930) AI 주식 분석 모델", "bold"))
    print(_c(f"  분석 시각: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "white"))
    print(_c(border, "cyan"))


def print_section(title: str):
    print(_c(f"\n{'─'*50}", "blue"))
    print(_c(f"  {title}", "bold"))
    print(_c(f"{'─'*50}", "blue"))


def print_score_bar(label: str, score: float, width: int = 20):
    """점수를 텍스트 바 차트로 시각화합니다."""
    center   = width // 2
    filled   = int(abs(score) / 10 * center)
    if score >= 0:
        bar = " " * center + _c("█" * filled, "green") + " " * (center - filled)
    else:
        bar = " " * (center - filled) + _c("█" * filled, "red") + " " * center

    color = "green" if score > 2 else "red" if score < -2 else "yellow"
    score_str = _c(f"{score:+6.2f}", color)
    print(f"  {label:<20} [{bar}] {score_str}")


def print_result(result: dict, verbose: bool = False):
    """분석 결과를 콘솔에 출력합니다."""

    # 신호 색상 매핑
    signal_color = {
        "strong_buy":  "green",
        "buy":         "green",
        "neutral":     "yellow",
        "sell":        "red",
        "strong_sell": "red",
    }
    sc = signal_color.get(result["signal"], "white")

    print_section("📊 분석 축별 점수 (각 -10 ~ +10)")
    axis_labels = {
        "technical":   "기술적 분석",
        "fundamental": "펀더멘탈",
        "financial":   "재무건전성",
        "macro":       "거시 환경",
        "sentiment":   "커뮤니티 감성",
    }
    for key, label in axis_labels.items():
        s = result["axis_scores"].get(key, 0.0)
        w = result["axis_weights"].get(key, 0.0)
        print_score_bar(f"{label}({w*100:.0f}%)", s)

    print_section("🎯 최종 분석 결과")
    total_score_str = f"{result['total_score']:+.2f}"
    print(f"\n  종합 점수:   {_c(total_score_str, sc)}")
    print(f"  신뢰도:      {result['confidence']:.1f}%")
    print(f"\n  매수/매도 의견: {_c(result['label'], sc)} ({_c(sc.upper(), sc)})")

    conf_note = ""
    if   result["confidence"] >= 80: conf_note = "★ 신호가 매우 강합니다"
    elif result["confidence"] >= 60: conf_note = "◎ 어느 정도 확신 있는 신호"
    elif result["confidence"] >= 40: conf_note = "△ 신호 강도가 약합니다. 추가 확인 권고"
    else:                             conf_note = "※ 혼재된 신호 — 관망 또는 소량 포지션 권장"
    print(f"  ({conf_note})")
    print()


def print_details(details_dict: dict, section_name: str, verbose: bool = False):
    """세부 지표 출력 (--verbose 옵션 시)."""
    if not verbose:
        return
    print_section(f"🔍 {section_name} 상세")
    for k, v in details_dict.items():
        print(f"  {k:<20}: {v}")


def run_analysis(force_mock: bool = False) -> dict:
    """
    전체 분석 파이프라인을 실행합니다.

    Args:
        force_mock: True이면 API 호출 없이 모의 데이터만 사용

    Returns:
        dict — SignalModel.predict()와 동일한 구조
    """
    # ── (1) 데이터 수집 ───────────────────────────────────────
    print(_c("\n🔄 데이터 수집 중...", "cyan"))
    from data_collector import DataCollector
    dc = DataCollector()

    price_df     = dc.get_price_data()
    fundamentals = dc.get_fundamentals()
    income_df    = dc.get_income_statement()
    balance_df   = dc.get_balance_sheet()
    cashflow_df  = dc.get_cashflow()
    insider      = dc.get_insider_trades()
    macro_data   = dc.get_macro_data()
    headlines    = dc.get_news_headlines()
    flow_data    = dc.get_investor_flow()

    print(_c(f"  ✓ 주가 데이터: {len(price_df)}거래일", "green"))
    print(_c(f"  ✓ 뉴스 헤드라인: {len(headlines)}건", "green"))

    # 엑셀 내보내기 대상 저장을 위해 dc 객체를 result에 잠시 담아둠
    dc_instance = dc

    # ── (2) 기술적 분석 ──────────────────────────────────────
    print(_c("\n🔬 기술적 분석 중...", "cyan"))
    from technical_analyzer import TechnicalAnalyzer
    ta         = TechnicalAnalyzer(price_df)
    ta_score   = ta.score()
    ta_details = ta.details()
    print(_c(f"  ✓ 기술적 점수: {ta_score:+.2f}", "green"))

    # ── (3) 펀더멘탈 분석 ────────────────────────────────────
    print(_c("\n💼 펀더멘탈 분석 중...", "cyan"))
    from fundamental_analyzer import FundamentalAnalyzer, FinancialAnalyzer
    fa         = FundamentalAnalyzer(fundamentals, insider, flow_data)
    fin        = FinancialAnalyzer(income_df, balance_df, cashflow_df)
    fa_score   = fa.score()
    fin_score  = fin.score()
    fa_details = fa.details()
    fin_details= fin.details()
    print(_c(f"  ✓ 펀더멘탈 점수:  {fa_score:+.2f}", "green"))
    print(_c(f"  ✓ 재무건전성 점수: {fin_score:+.2f}", "green"))

    # ── (4) 거시 환경 분석 ───────────────────────────────────
    print(_c("\n🌐 거시 환경 분석 중...", "cyan"))
    from macro_analyzer import MacroAnalyzer
    ma         = MacroAnalyzer(macro_data)
    ma_score   = ma.score()
    ma_details = ma.details()
    print(_c(f"  ✓ 거시 환경 점수: {ma_score:+.2f}", "green"))

    # ── (5) 커뮤니티 감성 분석 ──────────────────────────────
    print(_c("\n💬 커뮤니티 감성 분석 중...", "cyan"))
    from sentiment_analyzer import SentimentAnalyzer
    sa         = SentimentAnalyzer(headlines, flow_data)
    sa_score   = sa.score()
    sa_details = sa.details()
    print(_c(f"  ✓ 감성 점수: {sa_score:+.2f}", "green"))

    # ── (6) AI 신호 모델 ─────────────────────────────────────
    print(_c("\n🤖 AI 신호 모델 계산 중...", "cyan"))
    from signal_model import SignalModel
    model = SignalModel()
    model.set_scores(
        technical   = ta_score,
        fundamental = fa_score,
        financial   = fin_score,
        macro       = ma_score,
        sentiment   = sa_score,
    )
    result = model.predict()

    # ── (7) 상세 정보 부착 ──────────────────────────────────
    result["_details"] = {
        "technical":   ta_details,
        "fundamental": fa_details,
        "financial":   fin_details,
        "macro":       ma_details,
        "sentiment":   sa_details,
    }
    result["insider_trades"] = insider

    return result, model, dc_instance


def main():
    parser = argparse.ArgumentParser(
        description="삼성전자 AI 주식 분석 모델"
    )
    parser.add_argument("--json",    action="store_true", help="결과를 JSON 파일로 저장")
    parser.add_argument("--excel",   action="store_true", help="수집된 원본 데이터를 엑셀로 저장")
    parser.add_argument("--verbose", action="store_true", help="세부 지표 모두 출력")
    parser.add_argument("--mock",    action="store_true", help="모의 데이터로 실행 (테스트)")
    args = parser.parse_args()

    print_header()

    try:
        result, model, dc_instance = run_analysis(force_mock=args.mock)
    except Exception as e:
        print(_c(f"\n[오류] 분석 실패: {e}", "red"))
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # 결과 출력
    print_result(result, verbose=args.verbose)

    # 세부 지표 출력 (--verbose)
    if args.verbose:
        details = result.get("_details", {})
        print_details(details.get("technical",   {}), "기술적 분석",    True)
        print_details(details.get("fundamental", {}), "펀더멘탈 분석",  True)
        print_details(details.get("financial",   {}), "재무건전성 분석", True)
        print_details(details.get("macro",       {}), "거시 환경 분석",  True)
        print_details(details.get("sentiment",   {}), "커뮤니티 감성",   True)

    # JSON 저장 (--json)
    if args.json:
        # _details 항목 제외하고 저장 (깔끔한 출력)
        out = {k: v for k, v in result.items() if k != "_details"}
        filepath = "analysis_result.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        print(_c(f"\n📄 JSON 저장 완료: {filepath}", "cyan"))
        print(json.dumps(out, ensure_ascii=False, indent=2))

    # 엑셀 저장 (--excel)
    if args.excel:
        date_str = datetime.datetime.now().strftime("%Y%m%d")
        excel_filepath = f"samsung_stock_data_{date_str}.xlsx"
        dc_instance.export_to_excel(excel_filepath)

    print(_c("\n" + "═" * 60, "cyan"))
    print(_c("  ⚠️  본 분석은 참고용이며, 투자 손익의 책임은 투자자 본인에게 있습니다.", "yellow"))
    print(_c("═" * 60 + "\n", "cyan"))


if __name__ == "__main__":
    main()
