"""
BIST Çok Katmanlı Screener
Katman 1: Temel Filtreleme (Kârlılık, Tavan Oranı, Değer Düşüşü)
Katman 2: Gruplama (En Karlı, En Çok Değer Kaybeden, Tavan Oranı, KAP Haberleri)
Katman 3: Teknik Analiz ve Fiyat Tahmini
"""

import os
import re
import asyncio
import httpx
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, date, timedelta
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
from sklearn.linear_model import LinearRegression
from dotenv import load_dotenv
import warnings
warnings.filterwarnings('ignore')

# Load environment variables
load_dotenv()

# ============================================================
# 1. APP BAŞLATMA VE KONFİGÜRASYON
# ============================================================

app = FastAPI(title="BIST Screener API", version="1.0")

# CORS ayarları
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Environment Variables
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MONGO_URI = os.getenv("MONGODB_URI")

# Global Variables
CACHED_STOCK_LIST = []
LAST_UPDATE_DATE = None
USD_TRY_RATE = 38.0
USD_TRY_HISTORICAL = {2021: 8.9, 2022: 16.5, 2023: 23.5, 2024: 32.0, 2025: 36.0, 2026: 38.0}

# ============================================================
# 2. MODELLER
# ============================================================

class ChatRequest(BaseModel):
    user_id: str
    message: str

class ScreenerResponse(BaseModel):
    layer: int
    timestamp: str
    total_scanned: int
    matches: int
    results: list

# ============================================================
# 3. YEDEK BIST LİSTESİ
# ============================================================

FALLBACK_BIST_LIST = [
    "A1CAP", "AAV", "AEE", "AEFES", "AFYON", "AGESA", "AGHOL", "AGROT", "AHGAZ", "AKBNK",
    "AKCNS", "AKFGY", "AKFYE", "AKGRT", "AKMGH", "AKSA", "AKSEN", "AKSGY", "AKSUE", "ALARK",
    "ALBRK", "ALCAR", "ALCTL", "ALFAS", "ALGYO", "ALKA", "ALKIM", "ALMAD", "ALTNY", "ALVES",
    "ANELE", "ANGEN", "ANHYT", "ANSGR", "ARASE", "ARCLK", "ARDYZ", "ARENA", "ARSAN", "ARTMS",
    "ARZUM", "ASELS", "ASTOR", "ATAKP", "ATATP", "ATEKS", "ATSYH", "AVOD", "AVPGY", "AVTUR",
    "AYCES", "AYDEM", "AYGAZ", "AZTEK", "BAGFS", "BAKAB", "BALAT", "BANVT", "BARMA", "BATIS",
    "BEYAZ", "BFREN", "BIENP", "BIGCHEF", "BIMAS", "BINHO", "BIOEN", "BIZIM", "BJKAS", "BLCYT",
    "BNTAS", "BOBET", "BORLS", "BORSK", "BOSSA", "BRISA", "BRKO", "BRKSN", "BRKVY", "BRSAN",
    "BRYAT", "BSOKE", "BTCIM", "BUCIM", "BURCE", "BURVA", "BVSAN", "BYDNR", "CAHIT", "CANTE",
    "CASA", "CCOLA", "CELHA", "CEMAS", "CEMTS", "CMBTN", "CMENT", "CONSE", "COSMO", "CRFSA",
    "CUSAN", "CVKMD", "CWENE", "DAGI", "DAPGM", "DARDL", "DGATE", "DGGYO", "DGNMO", "DITAS",
    "DMRGD", "DMSAS", "DNISI", "DOAS", "DOCO", "DOGUB", "DOHOL", "DOKTA", "DURDO", "DYOBY",
    "EBEBK", "ECILC", "ECZYT", "EDATA", "EDIP", "EGEEN", "EGGUB", "EGPRO", "EGSER", "EKGYO",
    "EKOS", "EKSUN", "ELITE", "EMKEL", "ENJSA", "ENKAI", "ENSRI", "EPLAS", "ERCB", "EREGL",
    "ERSU", "ESCAR", "ESEN", "ETILR", "EUPWR", "EUREK", "EUYO", "EYGYO", "FADE", "FENER",
    "FLAP", "FMIZP", "FONET", "FORMT", "FORTE", "FRIGO", "FROTO", "FZLGY", "GARAN", "GARFA",
    "GBDEV", "GENIL", "GENTS", "GEREL", "GESAN", "GIPTA", "GLBMD", "GLYHO", "GMTAS", "GOKNR",
    "GOLTS", "GOODY", "GOZDE", "GRSEL", "GRTHO", "GSDHO", "GSRAY", "GUBRF", "GWIND", "GZNMI",
    "HALKB", "HATSN", "HEDEF", "HEKTS", "HKTM", "HLGYO", "HRKET", "HTTBT", "HUBVC", "HUNER",
    "HURGZ", "ICBCT", "ICUGS", "IDEAS", "IEYHO", "IHAAS", "IHEVA", "IHGZT", "IHLAS", "IHLGM",
    "INGRM", "INTEM", "INVEO", "INVES", "IPEKE", "ISATR", "ISBTR", "ISCTR", "ISDMR", "ISFIN",
    "ISGSY", "ISGYO", "ISKPL", "ISMEN", "ISSEN", "ITEKS", "IZENR", "IZINV", "IZMDC",
    "JANTS", "KAPEI", "KARSN", "KARTN", "KATMR", "KAYSE", "KBORU", "KCAER", "KCHOL", "KENT",
    "KFEIN", "KGYO", "KIMMR", "KLGYO", "KLMSN", "KLNMA", "KLRHO", "KLSER", "KMPUR", "KNFRT",
    "KONTR", "KONYE", "KORDS", "KOZAA", "KOZAL", "KRDMD", "KRGYO", "KRONT", "KRPLS", "KRSTL",
    "KRTEK", "KSTUR", "KTLEV", "KTSKR", "KUTPO", "KUYAS", "LIDER", "LIDFA", "LINK", "LKMNH",
    "LMKDC", "LOGOS", "LRSHO", "LUKSK", "MAALT", "MACKO", "MAKIM", "MAKTK", "MANAS", "MARKA",
    "MAVI", "MEDTR", "MEGAP", "MEGMT", "MEPET", "MERCN", "MERIT", "MERKO", "METRO", "METUR",
    "MGROS", "MHRGY", "MIATK", "MMPKT", "MPARK", "MRGYO", "MRSHL", "MSGYO", "MTRKS", "MTRYO",
    "MZHLD", "NATEN", "NETAS", "NIBAS", "NTGAZ", "NUGYO", "NUHCM", "OBAMS", "OBASE", "ODAS",
    "OFSYM", "ONCSM", "ORCA", "ORGE", "ORMA", "OSMEN", "OSTIM", "OTKAR", "OTTO", "OYAKC",
    "OYYAT", "OZKGY", "OZRDN", "OZSUB", "PAGYO", "PAMEL", "PAPIL", "PARSN", "PASEU", "PATEK",
    "PCILT", "PEKGY", "PENGD", "PENTA", "PETKM", "PETUN", "PGSUS", "PINSU", "PKART", "PKENT",
    "PLTUR", "PNLSN", "PNSUT", "POLHO", "POLTK", "PRDGS", "PRKAB", "PRKME", "PSGYO", "RAYSG",
    "REEDR", "RGYAS", "RNPOL", "RODRG", "RUBNS", "RYGYO", "RYSAS", "SAHOL", "SAMAT", "SANEL",
    "SANFM", "SANKO", "SARKY", "SASA", "SAYAS", "SDTTR", "SEGMN", "SEKFK", "SEKUR", "SELEC",
    "SELVA", "SEYKM", "SILVR", "SISE", "SKBNK", "SKTAS", "SMART", "SMRTG", "SNAAM", "SNGYO",
    "SNICA", "SNKRN", "SOKE", "SOKM", "SONME", "SRVGY", "SUMAS", "SUNTK", "SURGY", "SUWEN",
    "TABGD", "TARKM", "TATEN", "TATGD", "TAVHL", "TBORG", "TCELL", "TDGYO", "TEKTU", "TERA",
    "TETMT", "THYAO", "TKFEN", "TKNSA", "TLMAN", "TMPOL", "TMSN", "TNZTP", "TOASO", "TRCAS",
    "TRGYO", "TRILC", "TSKB", "TSPOR", "TTKOM", "TTRAK", "TUCLK", "TUKAS", "TUPRS", "TURGG",
    "TURSG", "UFUK", "ULAS", "ULKER", "UNLU", "USAK", "VAKBN", "VAKFN", "VAKKO", "VANET",
    "VBTYZ", "VERTU", "VERUS", "VESBE", "VESTL", "VKFYO", "VKGYO", "YAPRK", "YATAS", "YAYLA",
    "YEOTK", "YGYO", "YKBNK", "YONGA", "YYAPI", "YYLGD", "YUNSA", "ZEDUR", "ZRGYO"
]

# ============================================================
# 4. YARDIMCI FONKSİYONLAR
# ============================================================

async def get_usd_rate() -> float:
    """Güncel dolar kurunu çeker"""
    global USD_TRY_RATE
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.get("https://api.exchangerate-api.com/v4/latest/USD")
            if res.status_code == 200:
                data = res.json()
                USD_TRY_RATE = data['rates']['TRY']
                return USD_TRY_RATE
    except Exception as e:
        print(f"Dolar kuru çekilemedi: {e}")
    return USD_TRY_RATE

def get_usd_rate_historical(year: int) -> float:
    """Yıllık ortalama dolar kuru"""
    return USD_TRY_HISTORICAL.get(year, 30.0)

def calculate_rsi(prices: pd.Series, period: int = 14) -> float:
    """RSI hesaplama"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1] if not rsi.empty and not pd.isna(rsi.iloc[-1]) else 50.0

def calculate_macd(prices: pd.Series) -> dict:
    """MACD hesaplama"""
    exp1 = prices.ewm(span=12, adjust=False).mean()
    exp2 = prices.ewm(span=26, adjust=False).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=9, adjust=False).mean()
    
    if not macd.empty and not signal.empty:
        return {
            'macd': macd.iloc[-1],
            'signal': signal.iloc[-1],
            'histogram': (macd.iloc[-1] - signal.iloc[-1])
        }
    return {'macd': 0, 'signal': 0, 'histogram': 0}

def calculate_bollinger_bands(prices: pd.Series, period: int = 20) -> dict:
    """Bollinger Bantları hesaplama"""
    sma = prices.rolling(period).mean()
    std = prices.rolling(period).std()
    upper = sma + (std * 2)
    lower = sma - (std * 2)
    
    if not sma.empty and not std.empty:
        last_sma = sma.iloc[-1]
        last_std = std.iloc[-1]
        width = ((upper.iloc[-1] - lower.iloc[-1]) / last_sma) * 100 if last_sma > 0 else 0
        return {
            'upper': upper.iloc[-1],
            'lower': lower.iloc[-1],
            'width': width,
            'squeeze': width < 15
        }
    return {'upper': 0, 'lower': 0, 'width': 0, 'squeeze': False}

async def fetch_live_bist_symbols() -> list:
    """KAP / BIST resmi kaynaklarından güncel hisse kodlarını çeker"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    # 1. KAP API
    try:
        url = "https://www.kap.org.tr/tr/api/dis/bist-sirketler"
        async with httpx.AsyncClient(headers=headers, timeout=10.0) as client:
            res = await client.get(url)
            if res.status_code == 200:
                data = res.json()
                symbols = [item.get("kod") for item in data if item.get("kod")]
                symbols = [s.strip().upper() for s in symbols if s and len(s) >= 3]
                if len(symbols) > 100:
                    print(f"KAP API üzerinden {len(symbols)} adet güncel hisse çekildi.")
                    return sorted(list(set(symbols)))
    except Exception as e:
        print(f"KAP API hatası: {e}")

    # 2. BIST Sitesi
    try:
        url = "https://www.borsaistanbul.com/tr/sayfa/26/pay-piyasasi-sirketleri"
        async with httpx.AsyncClient(headers=headers, timeout=10.0) as client:
            res = await client.get(url)
            if res.status_code == 200:
                raw_symbols = re.findall(r'([A-Z0-9]{3,5})\.E', res.text)
                if len(raw_symbols) > 100:
                    print(f"Borsa İstanbul sitesinden {len(raw_symbols)} hisse çekildi.")
                    return sorted(list(set(raw_symbols)))
    except Exception as e:
        print(f"BIST sitesi hatası: {e}")

    print("Canlı servis ulaşılamadı. Yedek BIST listesi kullanılıyor.")
    return sorted(list(set(FALLBACK_BIST_LIST)))

async def get_daily_stock_list() -> list:
    """Günde 1 kez canlı güncelleme yapar ve belleğe alır"""
    global CACHED_STOCK_LIST, LAST_UPDATE_DATE
    today = date.today()

    if LAST_UPDATE_DATE != today or not CACHED_STOCK_LIST:
        print(f"[{today}] BIST hisseleri güncelleniyor...")
        CACHED_STOCK_LIST = await fetch_live_bist_symbols()
        LAST_UPDATE_DATE = today

    return CACHED_STOCK_LIST

async def get_layer1_results() -> list:
    """MongoDB'den en son Layer1 sonuçlarını alır"""
    if MONGO_URI:
        try:
            client = AsyncIOMotorClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            db = client["borsaanaliz1_db"]
            last = await db["screener_layer1"].find_one(sort=[("timestamp", -1)])
            client.close()
            if last:
                return last.get('results', [])
        except Exception as e:
            print(f"Layer1 veri çekme hatası: {e}")
    return []

async def get_layer2_results() -> dict:
    """MongoDB'den en son Layer2 sonuçlarını alır"""
    if MONGO_URI:
        try:
            client = AsyncIOMotorClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            db = client["borsaanaliz1_db"]
            last = await db["screener_layer2"].find_one(sort=[("timestamp", -1)])
            client.close()
            if last:
                return last
        except Exception as e:
            print(f"Layer2 veri çekme hatası: {e}")
    return {}

def save_to_mongodb(collection: str, data: dict):
    """Veriyi MongoDB'ye kaydeder"""
    if MONGO_URI:
        try:
            client = AsyncIOMotorClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            db = client["borsaanaliz1_db"]
            # Async olarak çalıştır
            asyncio.create_task(db[collection].insert_one(data))
            client.close()
        except Exception as e:
            print(f"MongoDB kayıt hatası ({collection}): {e}")

# ============================================================
# 5. KATMAN 1: TEMEL FİLTRELEME
# ============================================================

@app.get("/api/screener/layer1")
async def layer1_screener():
    """
    1. KATMAN: 
    - 2026 kârlılığı pozitif (TTM Net Kâr > 0)
    - 12 aylık tavan fiyatı / mevcut fiyat oranı en yüksek
    - Son 3 yılda dolar bazında şirket değeri düşen
    """
    stocks = await get_daily_stock_list()
    results = []
    usd_try = await get_usd_rate()
    
    print(f"Layer1 başladı: {len(stocks)} hisse taranıyor...")
    
    for symbol in stocks:
        try:
            ticker = yf.Ticker(f"{symbol}.IS")
            info = ticker.info
            
            # 1.1 2026 Kârlılığı (TTM Net Kâr > 0)
            financials = ticker.financials
            is_profitable = False
            net_income = 0
            
            if financials is not None and not financials.empty:
                if 'Net Income' in financials.index:
                    net_income_series = financials.loc['Net Income']
                    if not net_income_series.empty:
                        net_income = net_income_series.iloc[0]
                        is_profitable = net_income > 0
            
            if not is_profitable:
                continue
            
            # 1.2 12 Aylık Tavan Fiyatı / Mevcut Fiyat Oranı
            hist_1y = ticker.history(period="1y")
            if len(hist_1y) < 10:
                continue
                
            current_price = hist_1y['Close'].iloc[-1]
            year_high = hist_1y['High'].max()
            ceiling_ratio = year_high / current_price if current_price > 0 else 0
            
            # 1.3 Son 3 Yıl Dolar Bazında Değer Değişimi
            hist_3y = ticker.history(period="3y")
            if len(hist_3y) < 10:
                continue
                
            price_3y_ago = hist_3y['Close'].iloc[0]
            price_now = hist_3y['Close'].iloc[-1]
            shares = info.get('sharesOutstanding', 1)
            
            # 3 yıl önceki dolar kuru (yaklaşık)
            usd_try_3y = 18.5
            
            market_cap_usd_now = (price_now * shares) / usd_try
            market_cap_usd_3y = (price_3y_ago * shares) / usd_try_3y
            
            value_decline = market_cap_usd_now / market_cap_usd_3y if market_cap_usd_3y > 0 else 0
            
            # Sadece değer kaybedenler (%10'dan fazla düşüş)
            if value_decline >= 0.90 or value_decline == 0:
                continue
            
            # Kriterleri geçenleri ekle
            results.append({
                'symbol': symbol,
                'net_income': f"{net_income/1_000_000:.2f}M ₺",
                'net_income_raw': float(net_income),
                'ceiling_ratio': round(ceiling_ratio, 3),
                'value_decline': round((1 - value_decline) * 100, 2),
                'year_high': round(year_high, 2),
                'current_price': round(current_price, 2),
                'market_cap_usd': round(market_cap_usd_now / 1e9, 2)
            })
            
        except Exception as e:
            continue
    
    # Tavan oranına göre sırala (en yüksekten)
    results = sorted(results, key=lambda x: x['ceiling_ratio'], reverse=True)
    
    # MongoDB'ye kaydet
    save_to_mongodb("screener_layer1", {
        "timestamp": datetime.now(),
        "total_scanned": len(stocks),
        "matches": len(results),
        "results": results
    })
    
    return {
        'layer': 1,
        'timestamp': datetime.now().isoformat(),
        'total_scanned': len(stocks),
        'matches': len(results),
        'results': results
    }

# ============================================================
# 6. KATMAN 2: GRUPLAMA VE SIRALAMA
# ============================================================

@app.get("/api/screener/layer2")
async def layer2_screener():
    """
    2. KATMAN: Layer1 sonuçlarını 4 farklı kritere göre gruplama
    1- En Karlı 50 Hisse
    2- En Çok Değer Kaybeden 50 Hisse
    3- Tavan Oranı En Yüksek 50 Hisse
    4- KAP Haberlerine Göre Yükseliş Beklenen 50 Hisse
    """
    layer1_results = await get_layer1_results()
    
    if not layer1_results:
        return {"error": "Önce Layer1'i çalıştırın", "layer": 2}
    
    # 2.1 Kârlılığı En Yüksek 50 Hisse
    profit_sorted = sorted(
        layer1_results, 
        key=lambda x: x.get('net_income_raw', 0), 
        reverse=True
    )[:50]
    
    # 2.2 Dolar Bazında En Çok Değer Kaybeden 50 Hisse
    decline_sorted = sorted(
        layer1_results, 
        key=lambda x: x.get('value_decline', 0), 
        reverse=True
    )[:50]
    
    # 2.3 Tavan Oranı En Yüksek 50 Hisse
    ceiling_sorted = sorted(
        layer1_results, 
        key=lambda x: x.get('ceiling_ratio', 0), 
        reverse=True
    )[:50]
    
    # 2.4 KAP Haberleri Analizi (Yükseliş Beklentisi)
    kap_positive = await analyze_kap_news(layer1_results)
    
    # Sonuçları grupla
    grouped_results = {
        'most_profitable': [{'rank': i+1, **item} for i, item in enumerate(profit_sorted)],
        'most_declined': [{'rank': i+1, **item} for i, item in enumerate(decline_sorted)],
        'highest_ceiling': [{'rank': i+1, **item} for i, item in enumerate(ceiling_sorted)],
        'kap_positive': [{'rank': i+1, **item} for i, item in enumerate(kap_positive)]
    }
    
    # 2.5 Tüm listelerde ortak olan hisseler (En güçlü sinyaller)
    common_symbols = set([item['symbol'] for item in profit_sorted]) & \
                     set([item['symbol'] for item in decline_sorted]) & \
                     set([item['symbol'] for item in ceiling_sorted]) & \
                     set([item['symbol'] for item in kap_positive])
    
    common_stocks = [item for item in layer1_results if item['symbol'] in common_symbols]
    
    # MongoDB'ye kaydet
    save_to_mongodb("screener_layer2", {
        "timestamp": datetime.now(),
        "groups": grouped_results,
        "common_stocks": common_stocks,
        "common_count": len(common_stocks)
    })
    
    return {
        'layer': 2,
        'timestamp': datetime.now().isoformat(),
        'groups': grouped_results,
        'common_stocks': common_stocks,
        'common_count': len(common_stocks)
    }

async def analyze_kap_news(stocks: list) -> list:
    """KAP haberlerini analiz et ve yükseliş beklentisi olanları filtrele"""
    positive_stocks = []
    
    for stock in stocks[:30]:  # Her hisse için KAP kontrolü
        symbol = stock['symbol']
        try:
            url = f"https://www.kap.org.tr/tr/api/bildirim?sirketKodu={symbol}"
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    
                    # Son 30 günün haberlerini kontrol et
                    positive_keywords = ['kar', 'büyüme', 'artış', 'yükseliş', 'hedef', 'beklenti', 'pozitif']
                    negative_keywords = ['zarar', 'düşüş', 'azalış', 'olumsuz', 'uyarı']
                    
                    for item in data[:10]:  # Son 10 haberi kontrol et
                        title = item.get('baslik', '').lower()
                        content = item.get('ozet', '').lower()
                        full_text = title + " " + content
                        
                        has_positive = any(word in full_text for word in positive_keywords)
                        has_negative = any(word in full_text for word in negative_keywords)
                        
                        if has_positive and not has_negative:
                            positive_stocks.append(stock)
                            break
        except Exception as e:
            continue
    
    return positive_stocks[:50]

# ============================================================
# 7. KATMAN 3: GRAFİK ANALİZİ VE FİYAT TAHMİNİ
# ============================================================

@app.get("/api/screener/layer3")
async def layer3_screener():
    """
    3. KATMAN:
    - 2. KATMAN'daki hisseleri grafik analizi ile değerlendir
    - 6 ay sonrası fiyat tahmini (Linear Regression)
    - Teknik göstergeler: RSI, MACD, Bollinger Bantları
    - Getiri oranına göre sırala
    - Top 20 hisseyi listele
    """
    layer2_results = await get_layer2_results()
    
    if not layer2_results:
        return {"error": "Önce Layer2'yi çalıştırın", "layer": 3}
    
    # Tüm hisseleri topla (ortak hisseler öncelikli)
    symbols_to_analyze = []
    
    # Önce ortak hisseler
    for item in layer2_results.get('common_stocks', []):
        if item.get('symbol') not in symbols_to_analyze:
            symbols_to_analyze.append(item['symbol'])
    
    # Sonra diğer gruplardan
    for group in ['most_profitable', 'most_declined', 'highest_ceiling', 'kap_positive']:
        for item in layer2_results.get('groups', {}).get(group, []):
            if item.get('symbol') not in symbols_to_analyze:
                symbols_to_analyze.append(item['symbol'])
    
    results = []
    
    for symbol in symbols_to_analyze[:100]:  # Maksimum 100 hisse analiz et
        try:
            ticker = yf.Ticker(f"{symbol}.IS")
            
            # 2 yıllık veriyi çek
            hist = ticker.history(period="2y")
            if len(hist) < 100:
                continue
            
            close_prices = hist['Close'].values
            
            # 📈 Trend Analizi (Linear Regression)
            X = np.arange(len(close_prices)).reshape(-1, 1)
            y = close_prices.reshape(-1, 1)
            
            model = LinearRegression()
            model.fit(X, y)
            
            # 6 ay sonrası (yaklaşık 180 iş günü) tahmin
            future_days = 180
            future_X = np.array([[len(close_prices) + future_days]])
            predicted_price = model.predict(future_X)[0][0]
            
            current_price = close_prices[-1]
            expected_return = ((predicted_price / current_price) - 1) * 100 if current_price > 0 else 0
            
            # 📊 Teknik Göstergeler
            prices_series = pd.Series(close_prices)
            rsi = calculate_rsi(prices_series)
            macd = calculate_macd(prices_series)
            bb = calculate_bollinger_bands(prices_series)
            
            # Hareketli Ortalamalar
            ma50 = np.mean(close_prices[-50:]) if len(close_prices) >= 50 else current_price
            ma200 = np.mean(close_prices[-200:]) if len(close_prices) >= 200 else current_price
            
            # Volatilite (yıllık)
            returns = np.diff(close_prices) / close_prices[:-1]
            volatility = np.std(returns) * np.sqrt(252) * 100 if len(returns) > 0 else 0
            
            # Sadece pozitif getiri beklenenleri al
            if expected_return > 0:
                results.append({
                    'symbol': symbol,
                    'current_price': round(current_price, 2),
                    'predicted_price_6m': round(predicted_price, 2),
                    'expected_return': round(expected_return, 2),
                    'rsi': round(rsi, 2),
                    'macd': round(macd.get('signal', 0), 3),
                    'ma50': round(ma50, 2),
                    'ma200': round(ma200, 2),
                    'volatility': round(volatility, 2),
                    'bb_squeeze': bb.get('squeeze', False),
                    'trend_strength': round(model.coef_[0][0] * 100, 2)
                })
                
        except Exception as e:
            print(f"{symbol} analiz hatası: {e}")
            continue
    
    # Getiri oranına göre sırala (en yüksekten)
    results = sorted(results, key=lambda x: x['expected_return'], reverse=True)
    
    # Top 20 hisse
    top_20 = results[:20]
    
    # MongoDB'ye kaydet
    save_to_mongodb("screener_layer3", {
        "timestamp": datetime.now(),
        "total_analyzed": len(results),
        "top_20": top_20,
        "all_results": results
    })
    
    return {
        'layer': 3,
        'timestamp': datetime.now().isoformat(),
        'total_analyzed': len(results),
        'top_20': top_20,
        'all_results': results
    }

# ============================================================
# 8. TÜM KATMANLARI TEK SEÇİMDE ÇALIŞTIR
# ============================================================

@app.get("/api/screener/full")
async def full_screener():
    """Tüm katmanları sırayla çalıştır"""
    print(f"[{datetime.now()}] Tüm katmanlar başlatılıyor...")
    
    # Layer 1
    layer1 = await layer1_screener()
    
    # Layer 2
    layer2 = await layer2_screener()
    
    # Layer 3
    layer3 = await layer3_screener()
    
    return {
        'timestamp': datetime.now().isoformat(),
        'layer1': {
            'matches': layer1.get('matches', 0),
            'top_results': layer1.get('results', [])[:10]
        },
        'layer2': {
            'common_stocks': layer2.get('common_stocks', []),
            'common_count': layer2.get('common_count', 0),
            'groups': layer2.get('groups', {})
        },
        'layer3': {
            'top_20': layer3.get('top_20', []),
            'total_analyzed': layer3.get('total_analyzed', 0)
        }
    }

# ============================================================
# 9. HİSSE DETAY ENDPOINT'İ
# ============================================================

@app.get("/api/stock/{symbol}")
async def get_stock_info(symbol: str):
    """Tek bir hissenin detaylı verilerini getir"""
    try:
        ticker_symbol = f"{symbol.upper()}.IS" if not symbol.endswith(".IS") else symbol.upper()
        ticker = yf.Ticker(ticker_symbol)
        
        history = ticker.history(period="1d")
        if history.empty:
            return {"error": "Hisse verisi bulunamadı."}
        
        current_price = history['Close'].iloc[-1]
        
        # Yıllık Bilanço Kâr Verileri
        financials = ticker.financials
        profit_data = {}
        
        if financials is not None and not financials.empty:
            if 'Net Income' in financials.index:
                net_incomes = financials.loc['Net Income']
                for d, val in net_incomes.items():
                    if pd.notna(val):
                        year = str(d.year)
                        profit_data[year] = f"{val / 1_000_000:,.2f} M TL"
        
        # Teknik göstergeler
        hist_6m = ticker.history(period="6mo")
        if len(hist_6m) > 20:
            rsi = calculate_rsi(hist_6m['Close'])
            macd = calculate_macd(hist_6m['Close'])
            bb = calculate_bollinger_bands(hist_6m['Close'])
        else:
            rsi, macd, bb = 50, {'signal': 0}, {'squeeze': False}
        
        info = ticker.info
        
        return {
            "symbol": symbol.upper(),
            "price": f"{current_price:.2f} TL",
            "profits": profit_data if profit_data else "Bilanço verisi bulunamadı",
            "technical": {
                "rsi": round(rsi, 2),
                "macd": round(macd.get('signal', 0), 3),
                "bb_squeeze": bb.get('squeeze', False)
            },
            "info": {
                "market_cap": info.get('marketCap', 0),
                "pe_ratio": info.get('trailingPE', 0),
                "beta": info.get('beta', 0),
                "dividend_yield": info.get('dividendYield', 0)
            }
        }
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# 10. BIST LİSTE ENDPOINT'İ
# ============================================================

@app.get("/api/stocks/list")
async def get_stock_list():
    """BIST hisse listesini getir"""
    stocks = await get_daily_stock_list()
    return {"stocks": stocks}

# ============================================================
# 11. AI CHAT ENDPOINT'İ (GEMINI)
# ============================================================

@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Gemini AI ile sohbet"""
    if not GEMINI_API_KEY:
        return {"reply": "Hata: GEMINI_API_KEY tanımlı değil!", "retry_after": 0}

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={GEMINI_API_KEY}"
    payload = {"contents": [{"parts": [{"text": request.message}]}]}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, timeout=30.0)
            data = response.json()

            if response.status_code == 429:
                return {"reply": "Ücretsiz kullanım kotasına ulaşıldı.", "retry_after": 40}

            if response.status_code != 200:
                return {"reply": f"Gemini API Hatası ({response.status_code})", "retry_after": 0}

            ai_reply = data["candidates"][0]["content"]["parts"][0]["text"]

            # MongoDB'ye kaydet
            if MONGO_URI:
                try:
                    client_db = AsyncIOMotorClient(MONGO_URI, serverSelectionTimeoutMS=5000)
                    db = client_db["borsaanaliz1_db"]
                    await db["chat_history"].insert_one({
                        "user_id": request.user_id,
                        "user_message": request.message,
                        "bot_response": ai_reply,
                        "timestamp": datetime.now()
                    })
                    client_db.close()
                except Exception as db_err:
                    print(f"DB Kayıt Hatası: {db_err}")

            return {"reply": ai_reply, "retry_after": 0}

        except Exception as e:
            return {"reply": f"Sunucu Bağlantı Hatası: {str(e)}", "retry_after": 0}

# ============================================================
# 12. ANA SAYFA (HTML)
# ============================================================

@app.get("/")
async def read_index():
    return FileResponse("index.html")

# ============================================================
# 13. OTOMATİK ZAMANLANMIŞ GÖREV
# ============================================================

@app.on_event("startup")
async def startup_event():
    """Uygulama başladığında otomatik taramayı başlat"""
    asyncio.create_task(scheduled_analysis())
    print(f"[{datetime.now()}] 🔄 Uygulama başlatıldı, otomatik analiz zamanlandı.")

async def scheduled_analysis():
    """Her 15 dakikada bir tam analiz yap"""
    while True:
        try:
            print(f"[{datetime.now()}] 🔄 Otomatik analiz başlıyor...")
            
            # Tüm katmanları çalıştır
            await layer1_screener()
            await layer2_screener()
            await layer3_screener()
            
            print(f"[{datetime.now()}] ✅ Otomatik analiz tamamlandı")
            
        except Exception as e:
            print(f"[{datetime.now()}] ❌ Otomatik analiz hatası: {e}")
        
        # 15 dakika bekle (900 saniye)
        await asyncio.sleep(900)

# ============================================================
# 14. UYGULAMA BAŞLATMA
# ============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
