import os
import yfinance as yf
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
from config import TICKER_YF

MODEL_PATH = "xgboost_model.json"

def calculate_technical_features(df):
    """과거 주가 데이터로 기술적 피처를 계산합니다."""
    # 간단한 이동평균선
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()
    
    # RSI (14일)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # MACD
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    
    # 변동성 및 추세
    df['Volatility'] = df['Close'].rolling(window=20).std()
    df['Price_Change'] = df['Close'].pct_change()
    
    return df

def get_latest_features():
    """오늘 날짜 기준 가장 최신의 특징(Feature) 벡터를 가져옵니다."""
    ticker = yf.Ticker(TICKER_YF)
    # 기술적 피처를 구하기 위해 최근 100일 스캔
    df = ticker.history(period="100d")
    df = calculate_technical_features(df)
    df.dropna(inplace=True)
    
    if df.empty:
        return None
        
    latest = df.iloc[-1]
    features = ['Close', 'Volume', 'MA5', 'MA20', 'MA60', 'RSI', 'MACD', 'MACD_Signal', 'Volatility', 'Price_Change']
    X_today = pd.DataFrame([latest[features].values], columns=features)
    return X_today

def predict_today():
    """XGBoost 모델을 로드하여 오늘의 단기 주가 상승 확률을 예측합니다."""
    if not os.path.exists(MODEL_PATH):
        return None
        
    X_today = get_latest_features()
    if X_today is None:
        return None
        
    clf = xgb.XGBClassifier()
    clf.load_model(MODEL_PATH)
    
    # 클래스 1(상승) 확률 반환
    prob = clf.predict_proba(X_today)[0][1]
    return float(prob)

def train_xgboost_optimizer():
    print("⏳ yfinance에서 과거 주가 데이터 수집 중 (최대 5년)...")
    ticker = yf.Ticker(TICKER_YF)
    df = ticker.history(period="5y")
    
    if df.empty:
        print("❌ 데이터를 가져오지 못했습니다.")
        return
        
    df = calculate_technical_features(df)
    
    df['Target_Return'] = df['Close'].shift(-5) / df['Close'] - 1
    df['Target'] = (df['Target_Return'] > 0).astype(int)
    
    df.dropna(inplace=True)
    
    features = ['Close', 'Volume', 'MA5', 'MA20', 'MA60', 'RSI', 'MACD', 'MACD_Signal', 'Volatility', 'Price_Change']
    X = df[features]
    y = df['Target']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)
    
    print("🤖 XGBoost 단기 주가 스윙 예측 모델 훈련 중...")
    clf = xgb.XGBClassifier(
        n_estimators=100, 
        max_depth=4, 
        learning_rate=0.05, 
        eval_metric='logloss',
        random_state=42
    )
    clf.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)
    
    train_acc = clf.score(X_train, y_train)
    test_acc = clf.score(X_test, y_test)
    print(f"  ✓ 훈련 정확도: {train_acc*100:.1f}% | 검증 정확도: {test_acc*100:.1f}%")
        
    clf.save_model(MODEL_PATH)
    print(f"💾 XGBoost 모델 저장 완료: {MODEL_PATH}")

if __name__ == "__main__":
    train_xgboost_optimizer()
