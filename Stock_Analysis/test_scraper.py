# -*- coding: utf-8 -*-
import requests
from bs4 import BeautifulSoup
import json
import traceback

def test_naver_news():
    print("=== NAVER NEWS TEST ===")
    ticker = "005930"
    headlines = []
    
    # Method 1: news_news.naver
    try:
        url = f"https://finance.naver.com/item/news_news.naver?code={ticker}&page=1"
        r = requests.get(url, timeout=5, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        soup = BeautifulSoup(r.text, "html.parser")
        links = soup.select(".tit")
        print(f"news_news.naver returned {len(links)} links")
        for a in links[:5]:
            print("  -", a.get_text(strip=True))
    except Exception as e:
        print("Method 1 Error:", e)

    # Method 2: main.naver
    try:
        url2 = f"https://finance.naver.com/item/main.naver?code={ticker}"
        r2 = requests.get(url2, timeout=5, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        soup2 = BeautifulSoup(r2.text, "html.parser")
        links2 = soup2.select("div.sub_section.news_section ul li > span > a.tit")
        if not links2:
             # try alternate selector
             links2 = soup2.select("div.sub_section.news_section ul li a")
        print(f"\nmain.naver returned {len(links2)} links")
        for a in links2[:5]:
            print("  -", a.get_text(strip=True))
    except Exception as e:
        print("Method 2 Error:", e)

def test_dart():
    print("\n=== DART API TEST ===")
    try:
        from config import DART_API_KEY
        if not DART_API_KEY or DART_API_KEY == "YOUR_DART_API_KEY_HERE":
            print("DART_API_KEY is not set.")
            return
            
        url = f"https://opendart.fss.or.kr/api/elestock.json?crtfc_key={DART_API_KEY}&corp_code=00126380"
        r = requests.get(url, timeout=5).json()
        print('Status:', r.get('status'), 'Message:', r.get('message'))
        if 'list' in r:
            print('Trades count:', len(r['list']))
            for obj in r['list'][:5]:
                print(f"Date: {obj.get('rcept_dt')} | Name: {obj.get('reprror')} | Shares: {obj.get('sp_stck_inc_dec_qy')} | Price: {obj.get('aqts_dsps_untsn')}")
        else:
            print("No 'list' in response:", list(r.keys()))
    except Exception as e:
        print("DART Error:", e)
        traceback.print_exc()

if __name__ == "__main__":
    test_naver_news()
    test_dart()
