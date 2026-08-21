import os
import httpx
import re
import pandas as pd
import yfinance as yf
from datetime import date
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient

app = FastAPI()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MONGO_URI = os.getenv("MONGODB_URI")

# Günlük Önbellek (Cache)
CACHED_STOCK_LIST = []
LAST_UPDATE_DATE = None

class ChatRequest(BaseModel):
    user_id: str
    message: str

# İnternet bağlantısı kesilirse kullanılacak yedek (fallback) hisse listesi
FALLBACK_BIST_LIST = [
    "A1CAP", "AAV", "AEE", "AEFES", "AFYON", "AGESA", "AGHOL", "AGROT", "AHGAZ", "AKBNK",
    "AKCNS", "AKFGY", "AKFYE", "AKGRT", "AKMGH", "AKSA", "AKSEN", "AKSGY", "AKSUE", "ALARK",
    "ALBRK", "ALCAR", "ALCTL", "ALFAS", "ALGYO", "ALKA", "ALKIM", "ALMAD", "ALTNY", "ALVES",
    "ANELE", "ANGEN", "ANHYT", "ANSGR", "ARASE", "ARCLK", "ARDYZ", "ARENA", "ARSAN", "ARTMS",
    "ARZUM", "ASELS", "ASTOR", "ATAKP", "ATATP", "ATEKS", "ATSYH", "AVOD", "AVPGY", "AVTUR",
    "AYCES", "AYDEM", "AYGAZ", "AZTEK", "BAGFS", "BAKAB", "BALAT", "BANVT", "BARMA", "BATIS",
    "BEYAZ", "BFREN", "BIENP", "BIGCHEFS", "BIMAS", "BINHO", "BIOEN", "BIZIM", "BJKAS", "BLCYT",
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
    "ISGSY", "ISGYO", "ISKPL", "ISMEN", "ISSEN", "ITEKS", "IWW", "IZENR", "IZINV", "IZMDC",
    "JANTS", "KAPEI", "KARSN", "KARTN", "KATMR", "KAYSE", "KBORU", "KCAER", "KCHOL", "KENT",
    "KFEIN", "KGYO", "KIMMR", "KLGYO", "KLMSN", "KLNMA", "KLRHO", "KLSER", "KMPUR", "KNFRT",
    "KONTR", "KONYE", "KORDS", "KOZAA", "KOZAL", "KRDMD", "KRGYO", "KRONT", "KRPLS", "KRSTL",
    "KRTEK", "KSTUR", "KTLEV", "KTSKR", "KUTPO", "KUYAŞ", "LIDER", "LIDFA", "LINK", "LKMNH",
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

async def fetch_live_bist_symbols():
    """KAP / BIST resmi kaynaklarından güncel hisse kodlarını canlı çeker"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    # 1. Deneme: KAP (Kamuyu Aydınlatma Platformu) Resmi API
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
        print(f"KAP API canlı çekim hatası: {e}")

    # 2. Deneme: BIST Veri Servisi Alternatifi
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
        print(f"Borsa Istanbul canlı çekim hatası: {e}")

    # Canlı çekim başarısız olursa yedek listeyi dön
    print("Canlı servis ulaşılamadı. Yedek BIST listesi kullanılıyor.")
    return sorted(list(set(FALLBACK_BIST_LIST)))

async def get_daily_stock_list():
    """Günde 1 kez canlı güncelleme yapar ve belleğe alır"""
    global CACHED_STOCK_LIST, LAST_UPDATE_DATE
    today = date.today()

    if LAST_UPDATE_DATE != today or not CACHED_STOCK_LIST:
        print(f"[{today}] Günün ilk isteği: BIST Hisse senetleri canlı olarak sorgulanıyor...")
        CACHED_STOCK_LIST = await fetch_live_bist_symbols()
        LAST_UPDATE_DATE = today

    return CACHED_STOCK_LIST

@app.get("/api/stocks/list")
async def get_stock_list():
    stocks = await get_daily_stock_list()
    return {"stocks": stocks}

@app.get("/api/stock/{symbol}")
async def get_stock_info(symbol: str):
    try:
        ticker_symbol = f"{symbol.upper()}.IS" if not symbol.endswith(".IS") else symbol.upper()
        ticker = yf.Ticker(ticker_symbol)
        
        # 15 dakika gecikmeli canlı borsa verisi
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
        
        return {
            "symbol": symbol.upper(),
            "price": f"{current_price:.2f} TL",
            "profits": profit_data if profit_data else "Bilanço verisi bulunamadı"
        }
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/chat")
async def chat(request: ChatRequest):
    if not GEMINI_API_KEY:
        return {"reply": "Hata: GEMINI_API_KEY tanımlı değil!", "retry_after": 0}

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={GEMINI_API_KEY}"
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

            if MONGO_URI:
                try:
                    mongo_client = AsyncIOMotorClient(MONGO_URI, serverSelectionTimeoutMS=5000)
                    db = mongo_client["borsaanaliz1_db"]
                    await db["chat_history"].insert_one({
                        "user_id": request.user_id,
                        "user_message": request.message,
                        "bot_response": ai_reply
                    })
                    mongo_client.close()
                except Exception as db_err:
                    print(f"DB Kayıt Hatası: {db_err}")

            return {"reply": ai_reply, "retry_after": 0}

        except Exception as e:
            return {"reply": f"Sunucu Bağlantı Hatası: {str(e)}", "retry_after": 0}

@app.get("/")
async def read_index():
    return FileResponse("index.html")
