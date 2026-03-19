import requests
from config import DART_API_KEY
from bs4 import BeautifulSoup

def test_dart():
    print("=== DART API TEST ===")
    url = f"https://opendart.fss.or.kr/api/elestock.json?crtfc_key={DART_API_KEY}&corp_code=00126380"
    try:
        r = requests.get(url, timeout=5).json()
        print('Status:', r.get('status'), 'Message:', r.get('message'))
        if 'list' in r:
            print('Trades count:', len(r['list']))
            for obj in r['list'][:5]:
                print(f"{obj.get('rcept_dt')} | {obj.get('reprror')} | {obj.get('isu_exn_nm')} | shares:{obj.get('sp_stck_inc_dec_qy')} | price:{obj.get('aqts_dsps_untsn')}")
    except Exception as e:
        print("DART Error:", e)

def test_naver_news():
    print("\n=== NAVER NEWS TEST ===")
    
    # Method 1: Main page
    try:
        url2 = 'https://finance.naver.com/item/main.naver?code=005930'
        r2 = requests.get(url2, timeout=5, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(r2.text, 'html.parser')
        links = soup.select('div.sub_section.news_section ul li a')
        print('News 1 (main.naver):')
        for a in links:
            print("  -", a.get_text(strip=True))
    except Exception as e:
        print("News 1 Error:", e)

    # Method 2: News page
    try:
        url3 = 'https://finance.naver.com/item/news_news.naver?code=005930&page=1'
        r3 = requests.get(url3, timeout=5, headers={'User-Agent': 'Mozilla/5.0'})
        soup3 = BeautifulSoup(r3.text, 'html.parser')
        links3 = soup3.select('a.tit')
        print('\nNews 2 (news_news.naver):')
        for a in links3:
            print("  -", a.get_text(strip=True))
    except Exception as e:
        print("News 2 Error:", e)

if __name__ == "__main__":
    test_dart()
    test_naver_news()
