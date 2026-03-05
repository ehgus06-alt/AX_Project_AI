import yfinance as yf
import pandas as pd
import pandas_ta as ta
import matplotlib.pyplot as plt

# 1. 주식 데이터 가져오기 (이 부분을 수정했습니다!)
ticker = "NFLX"
# download 대신 Ticker 객체의 history 메서드를 사용하면 MultiIndex 에러를 피할 수 있습니다.
stock_info = yf.Ticker(ticker)
data = stock_info.history(period="1y")

# --- 기술적 분석(Feature Engineering) 시작 ---

# 2. RSI (상대강도지수, 기본값 14일) 추가
data.ta.rsi(length=14, append=True)

# 3. MACD (이동평균수렴확산지수) 추가
data.ta.macd(fast=12, slow=26, signal=9, append=True)

# 4. 결측치(NaN) 제거
data.dropna(inplace=True)

# --- 결과 확인 ---
print("=== 기술적 지표가 추가된 데이터 ===")
# 데이터의 열(Column)들이 어떻게 늘어났는지 확인 (우측으로 스크롤해서 보세요)
print(data.tail())

# RSI 차트 간단히 시각화
plt.figure(figsize=(10, 3))
plt.plot(data.index, data['RSI_14'], label='RSI (14)', color='purple')
plt.axhline(70, linestyle='--', color='red', alpha=0.5) 
plt.axhline(30, linestyle='--', color='green', alpha=0.5) 
plt.title(f"{ticker} RSI Indicator")
plt.legend()
plt.show()