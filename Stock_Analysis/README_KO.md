# 삼성전자 AI 주식 분석 모델 — 한국어 설명서

> **현재 날짜 기준 (2026-03-15)** 삼성전자(005930)에 특화된
> Python 기반 AI 매수/매도 의견 모델입니다.

---

## 📁 파일 구성 및 역할

```
stock_analysis/
├── config.py              ← 모든 설정값 (가중치, 임계값, 파라미터)
├── data_collector.py      ← 데이터 수집 (yfinance, FinanceDataReader)
├── technical_analyzer.py  ← 기술적 분석 모듈
├── fundamental_analyzer.py← 펀더멘탈 + 재무제표 분석 모듈
├── macro_analyzer.py      ← 거시 환경 분석 모듈
├── sentiment_analyzer.py  ← 커뮤니티 감성 분석 모듈
├── signal_model.py        ← AI 신호 앙상블 모델 (핵심)
├── main.py                ← 실행 진입점 (CLI)
├── requirements.txt       ← 필요 패키지 목록
└── README_KO.md           ← 이 파일
```

---

## 🚀 설치 및 실행

### 1. 패키지 설치

```bash
pip install -r requirements.txt
```

### 2. 실행 방법

```bash
# 기본 실행 (콘솔 출력)
python main.py

# 세부 지표까지 모두 출력
python main.py --verbose

# 결과를 JSON 파일(analysis_result.json)로 저장
python main.py --json

# 원본 수집 데이터를 엑셀(samsung_stock_data_YYYYMMDD.xlsx)로 저장
python main.py --excel

# REST API 서버 실행 (프론트/백엔드 연동용 최적)
# 실행 후 http://localhost:8080/docs 에서 API 테스트 가능
python api.py
```

### 3. API 키 설정 (DART)

내부자 거래(임원/대주주 매매 동향)를 정확히 수집하려면 금융감독원 DART API 키가 필요합니다.

1. [DART 오픈 API](https://opendart.fss.or.kr/)에서 인증키 신청 (무료)
2. `stock_analysis/config.py` 파일 상단의 `DART_API_KEY` 변수에 발급받은 키를 붙여넣기 해줍니다.

---

## 🏗️ 전체 분석 파이프라인

```
[DataCollector]
  yfinance / FinanceDataReader → 주가, 재무제표, 거시지표, 뉴스 수집
       ↓
[5가지 Analyzer] — 각각 -10 ~ +10점 산출
  ┌─ TechnicalAnalyzer   → RSI, MACD, 볼린저, MA, 스토캐스틱, OBV
  ├─ FundamentalAnalyzer → PER, PBR, ROE, 배당률, 내부자매매, 수급
  ├─ FinancialAnalyzer   → 영업이익추세, 매출성장, 부채비율, FCF, 영업이익률
  ├─ MacroAnalyzer       → 환율, SOX, 금리, 반도체재고, AI수요, 중국PMI
  └─ SentimentAnalyzer   → 뉴스헤드라인 키워드, 외국인·기관 수급
       ↓
[SignalModel]
  가중 앙상블 합산 → 신뢰도(확신도) 계산
       ↓
[최종 출력]
  🚀 강력매수 / 📈 매수 / ⚖️ 중립 / 📉 매도 / 🔻 강력매도
```

---

## 📊 분석 모듈 상세 설명

### 1. `config.py` — 설정 파일

모든 하이퍼파라미터를 한 곳에서 관리합니다.
**이 파일만 수정해도 모델의 판단 기준을 바꿀 수 있습니다.**

| 설정 섹션           | 주요 내용                                     |
| ------------------- | --------------------------------------------- |
| `WEIGHTS`           | 5개 분석 축의 가중치 (합계 = 1.0)             |
| `TECHNICAL`         | RSI 기간, 이동평균 기간, 볼린저 밴드 파라미터 |
| `FUNDAMENTAL`       | PER/PBR/ROE 구간 기준값                       |
| `FINANCIAL`         | 영업이익 성장률 기준값, 부채비율 기준값       |
| `MACRO`             | 환율 구간, SOX 변화율 기준, 금리 기준         |
| `SIGNAL_THRESHOLDS` | 강력매수/매수/중립/매도/강력매도 점수 임계값  |

**가중치 예시 (기본값):**

```python
WEIGHTS = {
    "technical":   0.25,   # 기술적 분석 25%
    "fundamental": 0.20,   # 펀더멘탈 20%
    "financial":   0.20,   # 재무건전성 20%
    "macro":       0.20,   # 거시 환경 20%
    "sentiment":   0.15,   # 커뮤니티 감성 15%
}
```

---

### 2. `data_collector.py` — 데이터 수집

`DataCollector` 클래스가 모든 데이터를 수집합니다.
실패 시 현실적 모의 데이터로 자동 대체되어 항상 실행 가능합니다.

| 메서드                   | 수집 데이터                  | 소스                           |
| ------------------------ | ---------------------------- | ------------------------------ |
| `get_price_data()`       | 일봉 OHLCV                   | yfinance / FinanceDataReader   |
| `get_fundamentals()`     | PER, PBR, BPS, 배당수익률 등 | **네이버 금융 스크래핑**       |
| `get_income_statement()` | 분기별 매출/영업이익/순이익  | yfinance                       |
| `get_balance_sheet()`    | 분기별 자산/부채/자본        | yfinance                       |
| `get_cashflow()`         | 분기별 영업CF/FCF            | yfinance                       |
| `get_insider_trades()`   | 내부자 매수/매도 내역        | **금융감독원 DART OPEN API**   |
| `get_macro_data()`       | 환율, SOX, 금리, KOSPI       | yfinance                       |
| `get_news_headlines()`   | 최신 뉴스 헤드라인 주소/제목 | **네이버 금융 스크래핑**       |
| `get_investor_flow()`    | 외국인·기관 5일 순매수       | FinanceDataReader지연시 크롤링 |

---

### 3. `technical_analyzer.py` — 기술적 분석

`TechnicalAnalyzer` 클래스가 주가 데이터로 6개 지표를 계산합니다.

| 지표             | 가중치 | 핵심 로직                                    |
| ---------------- | ------ | -------------------------------------------- |
| RSI (14일)       | 25%    | 30 이하 과매도→+7, 70 이상 과매수→-7         |
| MACD 히스토그램  | 25%    | 주가 대비 정규화, 골든크로스 +2점 보너스     |
| 볼린저 밴드 위치 | 20%    | 하단 이탈(0~10%)→+10, 상단 이탈(90~100%)→-10 |
| 이동평균 배열    | 20%    | 현가>MA5>MA20>MA60>MA120 정배열→+5           |
| 스토캐스틱       | 5%     | 과매도 구간 K>D 상향돌파 → 추가 +2점         |
| OBV 추세         | 5%     | OBV > EMA20 이면 +3                          |

**점수 해석:** 양수(+) → 매수 신호, 음수(-) → 매도 신호

---

### 4. `fundamental_analyzer.py` — 펀더멘탈 + 재무제표

두 개의 클래스로 구성됩니다:

**`FundamentalAnalyzer` (밸류에이션 + 내부자)**

| 지표          | 가중치 | 핵심 로직                        |
| ------------- | ------ | -------------------------------- |
| PER           | 30%    | 반도체 평균 14배 기준, PER<8→+10 |
| PBR           | 25%    | 순자산가치 대비, PBR<0.8→+10     |
| ROE           | 20%    | ROE≥15%→+8, ROE<0→-8             |
| 배당수익률    | 10%    | 4%이상→+4점 방어주 보너스        |
| 내부자 순매수 | 10%    | 금액 기준, 매수 비율>60%→+6      |
| 수급 방향     | 5%     | 외국인·기관 5일 순매수 시총 대비 |

**`FinancialAnalyzer` (재무건전성)**

| 지표               | 가중치 | 핵심 로직                  |
| ------------------ | ------ | -------------------------- |
| 영업이익 QoQ추세   | 35%    | 최신 3분기 가중 QoQ 성장률 |
| 매출 YoY성장률     | 20%    | YoY≥20%→+8                 |
| 부채비율           | 20%    | 50% 미만→+6, 200% 초과→-7  |
| FCF (잉여현금흐름) | 15%    | FCF>5조→+4, FCF<0→-2       |
| 영업이익률         | 10%    | 20% 이상→+10               |

---

### 5. `macro_analyzer.py` — 거시 환경

`MacroAnalyzer` 클래스가 7개 거시 지표를 분석합니다.

| 지표                | 가중치 | 삼성전자 관련성                    |
| ------------------- | ------ | ---------------------------------- |
| 원달러 환율         | 25%    | 수출기업 — 1,350~1,500이 최적 구간 |
| SOX 반도체 지수     | 20%    | 글로벌 반도체 수요 선행 지표       |
| 미 국채 10년물 금리 | 20%    | 금리 상승 → 성장주 밸류 압박       |
| 반도체 재고 일수    | 15%    | 재고 감소 → 수요 회복 신호         |
| AI 서버 수요 강도   | 10%    | HBM/DDR5 판매 견인                 |
| 중국 PMI            | 5%     | 중국 매출 비중 약 15%              |
| KOSPI 5일 변화      | 5%     | 시장 리스크 온/오프                |

**환율 특이사항:**
삼성전자는 수출 비중이 높아 **1,350~1,500 구간이 최적**입니다.
1,250 이하(강원화)면 수출 불리, 1,550 이상이면 외국인 이탈 우려로 점수가 낮아집니다.

---

### 6. `sentiment_analyzer.py` — 커뮤니티 감성 (딥러닝)

단순 단어 매칭 방식을 완전히 넘어서, 서울대학교가 배포한 한국어 금융 문맥 분석 모델 **KR-FinBERT-SC** 딥러닝 파이프라인을 사용합니다.

**뉴스 감성 딥러닝 분석 (55%)**

- 네이버 종목 뉴스를 실시간으로 스크래핑한 뒤 PyTorch `transformers` 엔진에 주입합니다.
- 복잡한 뉘앙스(예: "성장률 둔화 우려 속에 선방")를 가진 헤드라인의 **긍정/부정/중립 확률**을 AI가 0.0~1.0 체계로 직접 추론하고 환산합니다.

**외국인·기관 수급 (45%)**

- 외국인 5일 순매수 (60% 비중) + 기관 5일 순매수 (40% 비중)
- 삼성전자 하루 평균 거래대금 1조원 기준으로 정규화

---

### 7. `signal_model.py` — AI 신호 모델 (XGBoost 머신러닝 최적화)

`SignalModel` 클래스가 5개 점수를 받아 최종 신호를 결정합니다. 단순히 고정된 가중치를 곱하는 것을 넘어, **과거 5년간의 데이터를 주입받아 스스로 성장한 XGBoost 분류기**가 개입합니다.

**가중 앙상블 공식 & 동적 조절:**

- 기본적으로 설정된 5개 가중치를 할당받으나, `ml_optimizer.py`가 산출한 XGBoost 단기 방향 예측 모델이 작동합니다.
- XGBoost 모델이 **"단기 상승 확률 > 60%"**로 예측하면, 즉시 기술적/수급 모멘텀 가중치를 폭발적으로 높여주고 보너스 점수를 부여하는 방식으로 동작을 유연하게 바꿉니다.

**신뢰도(확신도) 계산:**

```
신뢰도 = (방향 일치도 × 50%) + (점수 절대크기 × 50%)
```

**신호 임계값:**
| 점수 구간 | 신호 |
|---------|------|
| ≥ 6.0 | 🚀 강력매수 |
| ≥ 2.0 | 📈 매수 |
| ≥ -2.0| ⚖️ 중립 |
| ≥ -6.0| 📉 매도 |
| < -6.0| 🔻 강력매도 |

---

## 🔧 파라미터 튜닝 가이드

### 가중치 조정 (`config.py`)

단기 트레이딩 전략 (기술적 분석 강화):

```python
WEIGHTS = {
    "technical":   0.40,  # 상향
    "fundamental": 0.15,
    "financial":   0.15,
    "macro":       0.20,
    "sentiment":   0.10,
}
```

장기 가치투자 전략 (펀더멘탈 강화):

```python
WEIGHTS = {
    "technical":   0.10,
    "fundamental": 0.35,  # 상향
    "financial":   0.30,  # 상향
    "macro":       0.20,
    "sentiment":   0.05,
}
```

---

## 🔌 프론트엔드 / 백엔드 연동 가이드

해당 파이썬 AI 모델을 Node.js, Spring Boot, React, Vue 등 외부 애플리케이션과 아주 쉽게 연동할 수 있도록 **FastAPI REST 서버 (`api.py`)**가 도입되었습니다.

### 방식 1. FastAPI REST API 연동 (권장)

`python api.py` 명령어로 서버를 띄우면, 8080번 포트에서 AI 분석 결과 제공을 대기합니다.
웹 프론트엔드(JavaScript)나 타 백엔드 서버에서 아래처럼 1초 만에 분석 결과를 당겨갈 수 있습니다.

**JavaScript(프론트엔드) Fetch 연동 예시:**

```javascript
// 버튼 클릭 시 AI 자동 분석 수행
async function fetchStockAnalysis() {
  try {
    const response = await fetch("http://localhost:8080/api/analyze");
    const aiData = await response.json();

    // UI에 결과 반영
    document.getElementById("score").innerText = aiData.label;
    document.getElementById("confidence").style.width = `${aiData.confidence}%`;
    console.log("XGBoost 모델 신뢰 확률:", aiData.xgboost_prob);
  } catch (error) {
    console.error("AI 서버 호출 실패:", error);
  }
}
```

이 방식을 사용하면 파이썬 종속성(PyTorch 등)은 딥러닝 백엔드 서버가 전부 짊어지고, 웹 서비스는 가벼운 통신망으로만 연동되어 실무적인 **마이크로서비스 아키텍처(MSA)**가 달성됩니다!

### JSON 구조 명세표 (API 반환값 기준)

프론트엔드에 넘겨줘야 할 데이터 스키마는 아래와 같습니다.

```json
{
  "ticker": "005930",
  "name": "삼성전자",
  "analysis_date": "2026-03-15 19:00:23",
  "signal": "neutral", // "strong_buy", "buy", "neutral", "sell", "strong_sell" (프론트 디자인 분기용)
  "label": "⚖️  중립", // 사용자에게 노출할 텍스트
  "total_score": 1.03, // 종합 신호 점수 (-10 ~ +10)
  "confidence": 35.1, // AI 신뢰도 (퍼센트율, UI에서 프로그레스 바 형태로 시각화하기 좋음)
  "axis_scores": {
    "technical": -2.0, // 기술적 분석 점수 (-10 ~ +10)
    "fundamental": 0.4, // 펀더멘탈 분석 점수 (-10 ~ +10)
    "financial": 7.9, // 재무 건전성 분석 점수 (-10 ~ +10)
    "macro": 1.38, // 거시 환경 분석 점수 (-10 ~ +10)
    "sentiment": -2.71 // 커뮤니티/수급 분석 점수 (-10 ~ +10)
  },
  "contributions": {
    // 각 점수에 가중치를 곱해 실제 최종 점수에 반영된 양
    "technical": -0.5,
    "fundamental": 0.08,
    "financial": 1.58,
    "macro": 0.276,
    "sentiment": -0.4065
  }
}
```

### 방식 2. 실무 데이터 열람 기능 (Excel 연동)

사용자나 운영자가 AI가 판단한 "근거 원본"을 보고 싶어할 땐, `--excel` 인자로 생성된 `samsung_stock_data_YYYYMMDD.xlsx` 파일을 백엔드에서 다운로드 응답(Response)으로 스트리밍해 주면 됩니다. 이 엑셀 파일에는 실시간 스크래핑된 수급, 내부자 매매결과, 차트값, 재무제표가 시트별로 분리되어 있습니다.

---

## ⚠️ 주의사항 및 면책 조항

1. **본 모델은 참고용 도구입니다.** 투자 손익의 최종 책임은 투자자 본인에게 있습니다.
2. **과거 패턴이 미래를 보장하지 않습니다.** 모든 기술적/정량적 분석은 과거 데이터 기반입니다.
3. **데이터 품질에 의존합니다.** API 제한, 데이터 지연, 수집 오류가 발생할 수 있습니다.
4. **단일 모델로 투자 결정을 내리지 마세요.** 다양한 분석 방법을 결합하여 판단하시기 바랍니다.

---

## 🌱 향후 개선 방향

| 개선 항목          | 방법                                        |
| ------------------ | ------------------------------------------- |
| 백테스팅 엔진 추가 | 과거 신호 기준 수익률 시뮬레이션            |
| 실시간 알림        | 신호 변화 시 Slack/카카오 메시지 발송       |
| 다종목 지원        | SK하이닉스(000660), TSMC($TSM) 등 비교 분석 |
