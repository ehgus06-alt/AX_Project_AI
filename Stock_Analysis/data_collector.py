# -*- coding: utf-8 -*-
"""
data_collector.py — 삼성전자 주식 분석을 위한 데이터 수집 모듈

[역할]
  yfinance와 FinanceDataReader를 통해 실제 시장 데이터를 수집합니다.
  각 Analyzer 클래스가 이 모듈을 통해 데이터를 받습니다.

[주요 수집 데이터]
  - 주가 OHLCV (일봉)
  - 재무제표 (분기별 매출, 영업이익, 순이익)
  - 매크로 지표 (환율, SOX, 국채금리)
  - 뉴스 헤드라인 (감성 분석용)
"""

import datetime
import warnings
import requests
import pandas as pd
import numpy as np

warnings.filterwarnings("ignore")

try:
    import yfinance as yf
    _YF_AVAILABLE = True
except ImportError:
    _YF_AVAILABLE = False
    print("[경고] yfinance가 설치되지 않았습니다. 'pip install yfinance'를 실행하세요.")

try:
    import FinanceDataReader as fdr
    _FDR_AVAILABLE = True
except ImportError:
    _FDR_AVAILABLE = False

from config import (
    TICKER_KRX, TICKER_YF, PRICE_LOOKBACK_DAYS
)


class DataCollector:
    """
    삼성전자 주가/재무/거시/뉴스 데이터를 수집하는 클래스.

    사용법:
        dc = DataCollector()
        price_df = dc.get_price_data()
        fundamentals = dc.get_fundamentals()
    """

    def __init__(self, ticker_yf: str = TICKER_YF, ticker_krx: str = TICKER_KRX):
        self.ticker_yf  = ticker_yf
        self.ticker_krx = ticker_krx
        self._yf_obj    = yf.Ticker(ticker_yf) if _YF_AVAILABLE else None
        self._cache: dict = {}

    # ─────────────────────────────────────────────────────────────
    # 1. 주가 데이터
    # ─────────────────────────────────────────────────────────────
    def get_price_data(self, days: int = PRICE_LOOKBACK_DAYS) -> pd.DataFrame:
        """
        일봉 OHLCV 데이터를 반환합니다.

        Returns:
            DataFrame — 컬럼: [Open, High, Low, Close, Volume]
                        인덱스: DatetimeIndex
        """
        if "price" in self._cache:
            return self._cache["price"]

        end   = datetime.date.today()
        start = end - datetime.timedelta(days=days)
        df    = None

        # 방법 1: yfinance
        if _YF_AVAILABLE:
            try:
                df = yf.download(
                    self.ticker_yf, start=str(start), end=str(end),
                    progress=False, auto_adjust=True
                )
                if df is not None and not df.empty:
                    # 멀티인덱스 컬럼 평탄화
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = df.columns.get_level_values(0)
                    df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
            except Exception as e:
                print(f"[경고] yfinance 오류: {e}")
                df = None

        # 방법 2: FinanceDataReader (fallback)
        if (df is None or df.empty) and _FDR_AVAILABLE:
            try:
                df = fdr.DataReader(self.ticker_krx, str(start), str(end))
                df = df.rename(columns={
                    "Open": "Open", "High": "High", "Low": "Low",
                    "Close": "Close", "Volume": "Volume"
                })
                df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
            except Exception as e:
                print(f"[경고] FinanceDataReader 오류: {e}")
                df = None

        # 방법 3: 실시간 수집 실패 처리
        if df is None or df.empty:
            print("[경고] 주가 데이터 수집 실패")
            # Return empty DataFrame rather than mock data
            df = pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])

        self._cache["price"] = df
        return df

    # ─────────────────────────────────────────────────────────────
    # 2. 펀더멘탈 / 재무제표 데이터
    # ─────────────────────────────────────────────────────────────
    def get_fundamentals(self) -> dict:
        """
        yfinance에서 주요 투자 지표를 수집합니다.

        Returns:
            dict — per, pbr, roe, eps, dividend_yield, market_cap, beta 등
        """
        if "fundamentals" in self._cache:
            return self._cache["fundamentals"]

        data = {}
        # 네이버 금융 스크래핑 방식으로 변경 (yfinance 부정확성 해결)
        try:
            url = f"https://finance.naver.com/item/main.naver?code={self.ticker_krx}"
            r = requests.get(url, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(r.text, "html.parser")

            def get_val(selector, default=float("nan")):
                try:
                    return float(soup.select_one(selector).text.replace(",", ""))
                except:
                    return default

            data = {
                "per": get_val("#_per"),
                "pbr": get_val("#_pbr"),
                "eps": get_val("#_eps"),
                "dividend_yield": get_val("#_dvr") / 100 if soup.select_one("#_dvr") else float("nan"),
                "market_cap": get_val("#_market_sum") * 100000000 if soup.select_one("#_market_sum") else float("nan"), # 억원 단위 환산
            }
            # 현재가 파싱
            blind_price = soup.select_one("div.today p.no_today span.blind")
            if blind_price:
                data["current_price"] = float(blind_price.text.replace(",", ""))

        except Exception as e:
            print(f"[경고] 네이버 금융 펀더멘탈 수집 실패: {e}")

        # 수집 실패 시 빈 딕셔너리 반환
        if not data or all(np.isnan(v) for v in data.values() if isinstance(v, float)):
            print("[경고] 펀더멘탈 수집 실패")
            data = {}

        self._cache["fundamentals"] = data
        return data

    def get_income_statement(self) -> pd.DataFrame:
        """
        분기별 손익계산서 (매출, 영업이익, 순이익) 반환.

        Returns:
            DataFrame — 컬럼: [revenue, operating_income, net_income]
                        인덱스: 분기 날짜
        """
        if "income" in self._cache:
            return self._cache["income"]

        df = pd.DataFrame()
        if _YF_AVAILABLE and self._yf_obj:
            try:
                qi = self._yf_obj.quarterly_income_stmt
                if qi is not None and not qi.empty:
                    df = qi.T.rename(columns={
                        "Total Revenue":     "revenue",
                        "Operating Income":  "operating_income",
                        "Net Income":        "net_income",
                    })
                    keep = [c for c in ["revenue", "operating_income", "net_income"] if c in df.columns]
                    df   = df[keep].dropna(how="all").sort_index()
            except Exception as e:
                print(f"[경고] 손익계산서 수집 실패: {e}")

        if df.empty:
            print("[경고] 손익계산서 데이터 수집 실패")
            df = pd.DataFrame(columns=["revenue", "operating_income", "net_income"])

        self._cache["income"] = df
        return df

    def get_balance_sheet(self) -> pd.DataFrame:
        """분기별 재무상태표 (총부채, 자기자본, 총자산) 반환"""
        if "balance" in self._cache:
            return self._cache["balance"]

        df = pd.DataFrame()
        if _YF_AVAILABLE and self._yf_obj:
            try:
                qb = self._yf_obj.quarterly_balance_sheet
                if qb is not None and not qb.empty:
                    df = qb.T.rename(columns={
                        "Total Assets":             "total_assets",
                        "Total Liabilities Net Minority Interest": "total_liabilities",
                        "Stockholders Equity":      "equity",
                        "Total Debt":               "total_debt",
                    })
                    keep = [c for c in ["total_assets", "total_liabilities", "equity", "total_debt"] if c in df.columns]
                    df   = df[keep].dropna(how="all").sort_index()
            except Exception as e:
                print(f"[경고] 재무상태표 수집 실패: {e}")

        if df.empty:
            print("[경고] 재무상태표 데이터 수집 실패")
            df = pd.DataFrame(columns=["total_assets", "total_liabilities", "equity", "total_debt"])

        self._cache["balance"] = df
        return df

    def get_cashflow(self) -> pd.DataFrame:
        """분기별 현금흐름표 (영업CF, 투자CF, CapEx, FCF) 반환"""
        if "cashflow" in self._cache:
            return self._cache["cashflow"]

        df = pd.DataFrame()
        if _YF_AVAILABLE and self._yf_obj:
            try:
                qc = self._yf_obj.quarterly_cashflow
                if qc is not None and not qc.empty:
                    df = qc.T.rename(columns={
                        "Operating Cash Flow":  "operating_cf",
                        "Investing Cash Flow":  "investing_cf",
                        "Capital Expenditure":  "capex",
                        "Free Cash Flow":       "fcf",
                    })
                    keep = [c for c in ["operating_cf", "capex", "fcf"] if c in df.columns]
                    df   = df[keep].dropna(how="all").sort_index()
                    # FCF 직접 계산 (없을 경우)
                    if "fcf" not in df.columns and "operating_cf" in df.columns and "capex" in df.columns:
                        df["fcf"] = df["operating_cf"] + df["capex"]  # capex는 음수
            except Exception as e:
                print(f"[경고] 현금흐름표 수집 실패: {e}")

        if df.empty:
            print("[경고] 현금흐름표 데이터 수집 실패")
            df = pd.DataFrame(columns=["operating_cf", "capex", "fcf"])

        self._cache["cashflow"] = df
        return df

    # ─────────────────────────────────────────────────────────────
    # 3. 내부자 거래 데이터
    # ─────────────────────────────────────────────────────────────
    def get_insider_trades(self) -> list[dict]:
        """
        DART API 대신 네이버 금융의 '외국인/기관 순매매' 동향을 내부자/주도세력 매매로 간주하여 수집합니다.
        (사용자 요청에 따라 DART 데이터가 간헐적으로 비어보이는 현상을 대체)

        Returns:
            list[dict] — 각 항목: {date, name, type('buy'/'sell'), shares, value}
        """
        if "insider" in self._cache:
            return self._cache["insider"]

        trades = []
        try:
            # 네이버 금융 종목별 투자자(외국인/기관) 매매동향 페이지 스크래핑
            url = f"https://finance.naver.com/item/frgn.naver?code={self.ticker_krx}"
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"}
            r = requests.get(url, timeout=5, headers=headers)
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(r.text, "html.parser")
            rows = soup.select("table.type2 tr[onmouseover]")
            
            # 현재가 가져오기 (매매대금 추산용)
            price = 60000
            if "price" in self._cache and not self._cache["price"].empty:
                val = self._cache["price"]["Close"].iloc[-1]
                price = float(val) if hasattr(val, '__float__') else 60000
            elif "fundamentals" in self._cache and "current_price" in self._cache["fundamentals"]:
                price = self._cache["fundamentals"]["current_price"]
                
            # 최근 10일치 데이터를 순회하며 거래 내역 생성 (UI에 풍부하게 표시하기 위함)
            for row in rows[:10]:
                cols = row.select("td")
                if len(cols) >= 7:
                    date_str = cols[0].text.strip().replace(".", "-")
                    try:
                        i_net_shares = int(cols[5].text.replace(",", ""))
                        f_net_shares = int(cols[6].text.replace(",", ""))
                        
                        if i_net_shares != 0:
                            trades.append({
                                "date": date_str,
                                "name": "기관계",
                                "type": "buy" if i_net_shares > 0 else "sell",
                                "shares": abs(i_net_shares),
                                "value": abs(i_net_shares) * price
                            })
                        if f_net_shares != 0:
                            trades.append({
                                "date": date_str,
                                "name": "외국인",
                                "type": "buy" if f_net_shares > 0 else "sell",
                                "shares": abs(f_net_shares),
                                "value": abs(f_net_shares) * price
                            })
                    except Exception: 
                        pass
        except Exception as e:
            print(f"[경고] 기관/외국인 대체 내부자 거래 수집 실패: {e}")

        self._cache["insider"] = trades
        return trades

    # ─────────────────────────────────────────────────────────────
    # 4. 거시 지표 데이터
    # ─────────────────────────────────────────────────────────────
    def get_macro_data(self) -> dict:
        """
        원달러 환율, SOX 지수, 미 국채 금리 등 거시 지표를 수집합니다.

        Returns:
            dict — exchange_rate, sox_5d_change, us10y_yield, kospi_5d_change 등
        """
        if "macro" in self._cache:
            return self._cache["macro"]

        result = {}
        if _YF_AVAILABLE:
            today = datetime.date.today()
            start = today - datetime.timedelta(days=30)

            def _fetch(ticker, column="Close"):
                try:
                    df = yf.download(ticker, start=str(start), end=str(today),
                                     progress=False, auto_adjust=True)
                    if df is not None and not df.empty:
                        if isinstance(df.columns, pd.MultiIndex):
                            df.columns = df.columns.get_level_values(0)
                        return df[column].dropna()
                except Exception:
                    pass
                return pd.Series(dtype=float)

            # 원달러 환율
            krw = _fetch("KRW=X")
            if not krw.empty:
                result["exchange_rate"]      = float(krw.iloc[-1])
                result["exchange_rate_5d"]   = float(krw.iloc[-1] - krw.iloc[-6]) if len(krw) >= 6 else 0.0
                result["exchange_rate_20d"]  = float(krw.iloc[-1] - krw.iloc[-21]) if len(krw) >= 21 else 0.0

            # SOX (필라델피아 반도체 지수)
            sox = _fetch("^SOX")
            if not sox.empty:
                result["sox_current"]  = float(sox.iloc[-1])
                result["sox_5d_change_pct"] = float(
                    (sox.iloc[-1] - sox.iloc[-6]) / sox.iloc[-6] * 100
                ) if len(sox) >= 6 else 0.0

            # 미 10년물 국채 금리
            t10y = _fetch("^TNX")
            if not t10y.empty:
                result["us10y_yield"] = float(t10y.iloc[-1])

            # KOSPI
            kospi = _fetch("^KS11")
            if not kospi.empty:
                result["kospi_current"] = float(kospi.iloc[-1])
                result["kospi_5d_change_pct"] = float(
                    (kospi.iloc[-1] - kospi.iloc[-6]) / kospi.iloc[-6] * 100
                ) if len(kospi) >= 6 else 0.0

            # WTI 원유
            wti = _fetch("CL=F")
            if not wti.empty:
                result["wti_oil"] = float(wti.iloc[-1])

        # 수집 실패 시 빈 딕셔너리 유지
        if not result:
            print("[경고] 거시 지표 수집 실패")

        # 추가 반도체 재고 지표 (크롤링 불가 → 모의)
        result.setdefault("semi_inventory_days", 58)   # 반도체 평균 재고 일수
        result.setdefault("ai_server_demand",    8.8)  # /10 스케일 (주관적)
        result.setdefault("fed_rate",            4.25) # 연방기금금리 %
        result.setdefault("china_pmi",           49.8) # 중국 제조업 PMI

        self._cache["macro"] = result
        return result

    # ─────────────────────────────────────────────────────────────
    # 5. 뉴스 헤드라인 수집
    # ─────────────────────────────────────────────────────────────
    def get_news_headlines(self, n: int = 30) -> list[str]:
        """
        네이버 검색의 '뉴스' 탭을 스크래핑하여 삼성전자와 확실히 관련된 최신 뉴스를 가져옵니다.
        (기존 news_news.naver는 동적 렌더링으로 인해 누락되는 현상 대체)

        Returns:
            list[str] — 최근 뉴스 제목 목록
        """
        if "news" in self._cache:
            return self._cache["news"]

        headlines = []
        try:
            url = f"https://finance.naver.com/item/main.naver?code={self.ticker_krx}"
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"}
            r = requests.get(url, timeout=5, headers=headers)
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(r.text, "html.parser")
            
            # 메인 페이지의 종목 뉴스 목록
            links = soup.select("div.sub_section.news_section ul li a")
            
            related_keywords = ["삼성", "전자", "반도체", "HBM", "파운드리", "코스피", "증시", "외인", "기관", "매수", "매도", "실적"]
            
            for a in links:
                text = a.get_text(strip=True)
                # 무관한 기사 필터링 (최소한의 연관 키워드가 있는지 확인)
                if text and any(kw in text for kw in related_keywords):
                    if text not in headlines: # 중복 방지
                        headlines.append(text)
                
                if len(headlines) >= n:
                    break
        except Exception as e:
            print(f"[경고] 네이버 종목 뉴스 스크래핑 실패: {e}")

        if not headlines:
            print("[경고] 모든 뉴스 헤드라인 수집 실패")

        self._cache["news"] = headlines
        return headlines

    # ─────────────────────────────────────────────────────────────
    # 6. 외국인/기관 수급 데이터
    # ─────────────────────────────────────────────────────────────
    def get_investor_flow(self) -> dict:
        """
        최근 외국인·기관 순매수 데이터를 수집합니다.
        FinanceDataReader를 통해 KRX 데이터를 수집합니다.

        Returns:
            dict — foreign_net: 외국인 5일 누적 순매수(원), inst_net: 기관 5일
        """
        if "flow" in self._cache:
            return self._cache["flow"]

        result = {}
        if _FDR_AVAILABLE:
            try:
                end   = datetime.date.today()
                start = end - datetime.timedelta(days=14)
                df    = fdr.DataReader(f"KRX/{self.ticker_krx}", str(start), str(end))
                if df is not None and not df.empty:
                    # FinanceDataReader 컬럼명은 버전마다 다를 수 있음
                    for col in df.columns:
                        if "외국인" in col or "Foreign" in col.title():
                            result["foreign_net_5d"] = float(df[col].tail(5).sum())
                        if "기관" in col or "Institution" in col.title():
                            result["inst_net_5d"] = float(df[col].tail(5).sum())
            except Exception as e:
                print(f"[경고] 수급 데이터 수집 실패: {e}")

        if not result or "foreign_net_5d" not in result:
            # FinanceDataReader 실패 시 네이버 금융 조회 (종목 투자자별 매매동향)
            try:
                url = f"https://finance.naver.com/item/frgn.naver?code={self.ticker_krx}"
                r = requests.get(url, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(r.text, "html.parser")
                rows = soup.select("table.type2 tr[onmouseover]")
                
                f_net_shares, i_net_shares = 0, 0
                for row in rows[:5]:
                    cols = row.select("td")
                    if len(cols) >= 7:
                        try:
                            # 5번 인덱스는 기관 순매매량, 6번 인덱스는 외국인 순매매량 (주식 수)
                            i_net_shares += int(cols[5].text.replace(",", ""))
                            f_net_shares += int(cols[6].text.replace(",", ""))
                        except: pass
                
                # 금액(원)이 아닌 주식 수 기준이지만 감성 분석 등에는 정규화되어서 들어감.
                # 더 정확하게 하려면 당일 종가를 곱할 수도 있음
                if f_net_shares != 0 or i_net_shares != 0:
                    # 근사치로 금액을 계산하기 위해 캐시된 주가를 시도
                    price = 60000
                    if "price" in self._cache and not self._cache["price"].empty:
                        price = self._cache["price"]["Close"].iloc[-1]
                        
                    result["foreign_net_5d"] = f_net_shares * price
                    result["inst_net_5d"]    = i_net_shares * price
            except Exception as e:
                print(f"[경고] 네이버 수급 데이터 스크래핑 실패: {e}")

        if not result:
            print("[경고] 수급 데이터 수집 실패")

        self._cache["flow"] = result
        return result

    # ─────────────────────────────────────────────────────────────
    # 7. 엑셀 내보내기 (Excel Export)
    # ─────────────────────────────────────────────────────────────
    def export_to_excel(self, filepath: str = "samsung_stock_data.xlsx"):
        """
        수집되어 캐시된 모든 데이터를 하나의 엑셀 파일(여러 시트)로 저장합니다.
        """
        print(f"\n💾 엑셀 저장 준비 중... ({filepath})")
        
        try:
            with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
                # 1. 주가 데이터 (price)
                if "price" in self._cache and not self._cache["price"].empty:
                    self._cache["price"].to_excel(writer, sheet_name="Price_Data")
                else:
                    pd.DataFrame(["No Price Data"]).to_excel(writer, sheet_name="Price_Data")
                    
                # 2. 펀더멘탈 (fundamentals)
                if "fundamentals" in self._cache and self._cache["fundamentals"]:
                    df_fund = pd.DataFrame(list(self._cache["fundamentals"].items()), columns=["Indicator", "Value"])
                    df_fund.to_excel(writer, sheet_name="Fundamentals", index=False)
                else:
                    pd.DataFrame(["No Fundamentals Data"]).to_excel(writer, sheet_name="Fundamentals")

                # 3. 손익계산서 (income)
                if "income" in self._cache and not self._cache["income"].empty:
                    self._cache["income"].to_excel(writer, sheet_name="Income_Statement")

                # 4. 재무상태표 (balance)
                if "balance" in self._cache and not self._cache["balance"].empty:
                    self._cache["balance"].to_excel(writer, sheet_name="Balance_Sheet")

                # 5. 현금흐름표 (cashflow)
                if "cashflow" in self._cache and not self._cache["cashflow"].empty:
                    self._cache["cashflow"].to_excel(writer, sheet_name="Cashflow")

                # 6. 내부자 거래 (insider)
                if "insider" in self._cache and self._cache["insider"]:
                    df_ins = pd.DataFrame(self._cache["insider"])
                    df_ins.to_excel(writer, sheet_name="Insider_Trades", index=False)
                else:
                    pd.DataFrame(columns=["date", "name", "type", "shares", "value"]).to_excel(writer, sheet_name="Insider_Trades", index=False)

                # 7. 거시 환경 지표 (macro)
                if "macro" in self._cache and self._cache["macro"]:
                    df_mac = pd.DataFrame(list(self._cache["macro"].items()), columns=["Indicator", "Value"])
                    df_mac.to_excel(writer, sheet_name="Macro_Environment", index=False)

                # 8. 뉴스 헤드라인 (news)
                if "news" in self._cache and self._cache["news"]:
                    df_news = pd.DataFrame(self._cache["news"], columns=["Headline"])
                    df_news.to_excel(writer, sheet_name="News_Headlines", index=False)
                else:
                    pd.DataFrame(columns=["Headline"]).to_excel(writer, sheet_name="News_Headlines", index=False)

                # 9. 투자자 수급 (flow)
                if "flow" in self._cache and self._cache["flow"]:
                    df_flow = pd.DataFrame(list(self._cache["flow"].items()), columns=["Indicator", "Value(KRW)"])
                    df_flow.to_excel(writer, sheet_name="Investor_Flow", index=False)
                    
            print(f"  ✓ 엑셀 원본 데이터 내보내기 완료: {filepath}")
            
        except ImportError:
            print("[경고] 엑셀 처리를 위해 openpyxl 패키지가 필요합니다. 'pip install openpyxl'을 실행해주세요.")
        except Exception as e:
            print(f"[오류] 엑셀 내보내기 실패: {e}")
