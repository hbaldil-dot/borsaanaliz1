"""
BIST Screener - Finnhub ile Gerçek Veri
"""

import os
import random
import httpx
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="BIST Screener", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")

# ============================================================
# 📊 TÜM BIST HİSSELERİ (GÜNCEL LİSTE)
# ============================================================

BIST_STOCKS = {
    # Bankalar
    "AKBNK": "Akbank",
    "GARAN": "Garanti BBVA",
    "ISCTR": "İş Bankası",
    "YKBNK": "Yapı Kredi",
    "VAKBN": "Vakıfbank",
    "HALKB": "Halkbank",
    "TSKB": "TSKB",
    "SKBNK": "Şekerbank",
    
    # Holdingler
    "KCHOL": "Koç Holding",
    "SAHOL": "Sabancı Holding",
    "DOHOL": "Doğan Holding",
    "OYAKC": "Oyak Çimento",
    
    # Havacılık - Ulaşım
    "THYAO": "Türk Hava Yolları",
    "PGSUS": "Pegasus",
    "TAVHL": "TAV Havalimanları",
    "DOAS": "Doğuş Otomotiv",
    "FROTO": "Ford Otosan",
    "TOASO": "Tofaş",
    "OTKAR": "Otokar",
    "TTRAK": "Türk Traktör",
    
    # Telekom - Teknoloji
    "TCELL": "Turkcell",
    "TTKOM": "Türk Telekom",
    "ASELS": "Aselsan",
    "VESTL": "Vestel",
    "ARCLK": "Arçelik",
    "NETAS": "Netaş",
    "INDES": "İndeks Bilgisayar",
    
    # Enerji - Petrol
    "TUPRS": "Tüpraş",
    "PETKM": "Petkim",
    "ENJSA": "Enerjisa",
    "AESAN": "Aesan",
    "AYEN": "Ayen Enerji",
    "ODAS": "Odaş Elektrik",
    
    # Gıda - Perakende
    "BIMAS": "BİM",
    "MGROS": "Migros",
    "SOKM": "ŞOK Marketler",
    "ULKER": "Ülker",
    "AEFES": "Anadolu Efes",
    "CCOLA": "Coca-Cola İçecek",
    "TUKAS": "Tukaş",
    "PINSU": "Pınar Su",
    "PNSUT": "Pınar Süt",
    "KENT": "Kent Gıda",
    
    # Demir - Çelik - Maden
    "EREGL": "Ereğli Demir Çelik",
    "KRDMD": "Kardemir",
    "ISDMR": "İskenderun Demir Çelik",
    "KOZAA": "Koza Altın",
    "KOZAL": "Koza Anadolu",
    "GUBRF": "Gübre Fabrikaları",
    "SASA": "Sasa Polyester",
    
    # Cam - Seramik - Yapı
    "SISE": "Şişe Cam",
    "CIMSA": "Çimsa",
    "BUCIM": "Batıçim",
    "GOLTS": "Göltaş Çimento",
    "BOLUC": "Bolu Çimento",
    "KONYA": "Konya Çimento",
    "KUTPO": "Kütahya Porselen",
    
    # Tekstil - Giyim
    "MAVI": "Mavi Giyim",
    "BOSSA": "Bossa",
    "SOKE": "Söke Tekstil",
    "YUNSA": "Yünsa",
    
    # Gayrimenkul
    "EKGYO": "Emlak Konut GYO",
    "TRGYO": "Torunlar GYO",
    "KGYO": "Kiler GYO",
    "DGGYO": "Doğuş GYO",
    "PAGYO": "Panora GYO",
    "VKGYO": "Vakıf GYO",
    
    # Sigorta - Finans
    "ANSGR": "Anadolu Sigorta",
    "AKGRT": "Aksigorta",
    "RAYSG": "Ray Sigorta",
    
    # Diğer
    "BRISA": "Brisa",
    "JANTS": "Jantsa",
    "KARSN": "Karsan",
    "KLMSN": "Klimasan",
    "LUKSK": "Lüks Kadıoğlu",
    "NIBAS": "Nibaş",
    "PRKAB": "Prysmian Kablo",
    "YATAS": "Yataş",
    "ZOREN": "Zorlu Enerji",
}

# ============================================================
# 🌐 FINNHUB İLE GERÇEK VERİ ÇEK
# ============================================================

async def get_stock_data_finnhub(symbol: str):
    """Finnhub API ile gerçek hisse verisi çek"""
    if not FINNHUB_API_KEY:
        return None
    
    try:
        finnhub_symbol = f"{symbol}.IS"
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Güncel fiyat
            quote_url = f"https://finnhub.io/api/v1/quote?symbol={finnhub_symbol}&token={FINNHUB_API_KEY}"
            quote_res = await client.get(quote_url)
            
            if quote_res.status_code != 200:
                return None
            
            quote_data = quote_res.json()
            
            # Fiyat var mı kontrol et
            if not quote_data.get("c", 0):
                return None
            
            # Şirket bilgileri
            profile_url = f"https://finnhub.io/api/v1/stock/profile2?symbol={finnhub_symbol}&token={FINNHUB_API_KEY}"
            profile_res = await client.get(profile_url)
            profile_data = profile_res.json() if profile_res.status_code == 200 else {}
            
            return {
                "symbol": symbol,
                "name": profile_data.get("name", BIST_STOCKS.get(symbol, symbol)),
                "price": round(quote_data.get("c", 0), 2),
                "change": round(quote_data.get("dp", 0), 2),
                "high": round(quote_data.get("h", 0), 2),
                "low": round(quote_data.get("l", 0), 2),
                "open": round(quote_data.get("o", 0), 2),
                "volume": int(quote_data.get("v", 0)),
                "currency": "TRY",
                "source": "Finnhub (Gerçek Veri)"
            }
    except Exception as e:
        print(f"Finnhub hatası ({symbol}): {e}")
        return None

# ============================================================
# 🌐 API ENDPOINTLERİ
# ============================================================

@app.get("/")
async def home():
    return FileResponse("index.html")

@app.get("/api/stocks")
async def get_stocks():
    """Tüm BIST hisselerini listele"""
    return {"stocks": list(BIST_STOCKS.keys())}

@app.get("/api/stock/{symbol}")
async def get_stock(symbol: str):
    """Hisse detayını getir - Finnhub gerçek veri, yoksa demo"""
    
    symbol = symbol.upper()
    
    if symbol not in BIST_STOCKS:
        return {"error": f"{symbol} BIST listesinde bulunamadı"}
    
    # 🔥 1. Finnhub ile gerçek veri dene
    data = await get_stock_data_finnhub(symbol)
    
    if data and data.get("price", 0) > 0:
        return data
    
    # 🔄 2. Gerçek veri yoksa demo veri döndür
    price = round(random.uniform(50, 500), 2)
    change = round(random.uniform(-5, 5), 2)
    
    return {
        "symbol": symbol,
        "name": BIST_STOCKS.get(symbol, symbol),
        "price": price,
        "change": change,
        "high": round(price * (1 + random.uniform(0.01, 0.04)), 2),
        "low": round(price * (1 - random.uniform(0.01, 0.04)), 2),
        "open": round(price * (1 + random.uniform(-0.02, 0.02)), 2),
        "volume": random.randint(100000, 5000000),
        "currency": "TRY",
        "source": "Demo Veri",
        "info": "⚠️ Gerçek veri alınamadı (Finnhub API anahtarı kontrol edin)"
    }

@app.post("/api/chat")
async def chat(request: dict):
    """AI Asistanı (Gemini)"""
    if not GEMINI_API_KEY:
        return {"reply": "API anahtarı eksik. Render Dashboard'a GEMINI_API_KEY ekleyin."}
    
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={GEMINI_API_KEY}"
        payload = {"contents": [{"parts": [{"text": request.get("message", "")}]}]}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
            data = response.json()
            
            if response.status_code == 200:
                reply = data["candidates"][0]["content"]["parts"][0]["text"]
                return {"reply": reply}
            else:
                return {"reply": f"API hatası: {response.status_code}"}
    except Exception as e:
        return {"reply": f"Hata: {str(e)}"}

# ============================================================
# 🚀 UYGULAMA BAŞLATMA
# ============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
