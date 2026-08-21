"""
BIST Screener - Alternatif Veri Kaynağı ile
"""

import os
import httpx
from datetime import datetime
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

# ============================================================
# 📊 BIST HİSSE LİSTESİ (Gerçek kodlar)
# ============================================================

BIST_STOCKS = {
    "THYAO": "Türk Hava Yolları",
    "ASELS": "Aselsan",
    "KCHOL": "Koç Holding",
    "SAHOL": "Sabancı Holding",
    "AKBNK": "Akbank",
    "GARAN": "Garanti BBVA",
    "ISCTR": "İş Bankası",
    "YKBNK": "Yapı Kredi",
    "TCELL": "Turkcell",
    "TTKOM": "Türk Telekom",
    "BIMAS": "BİM",
    "MGROS": "Migros",
    "EREGL": "Ereğli Demir Çelik",
    "FROTO": "Ford Otosan",
    "TOASO": "Tofaş",
    "TUPRS": "Tüpraş",
    "PETKM": "Petkim",
    "SISE": "Şişe Cam",
    "VESTL": "Vestel",
    "ARCLK": "Arçelik",
    "ENJSA": "Enerjisa",
    "PGSUS": "Pegasus",
    "TAVHL": "TAV Havalimanları",
    "DOAS": "Doğuş Otomotiv",
    "MAVI": "Mavi Giyim",
    "SASA": "Sasa Polyester",
    "CCOLA": "Coca-Cola İçecek",
    "AEFES": "Anadolu Efes",
    "ODAS": "Odaş Elektrik",
    "OYAKC": "Oyak Çimento",
}

# ============================================================
# 🌐 ALTERNATİF VERİ KAYNAĞI (Alpha Vantage / Finnhub / vb.)
# ============================================================

# NOT: Bu örnekte Finnhub API kullanıyoruz (ücretsiz)
# https://finnhub.io/register - buradan ücretsiz API anahtarı al

FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "dummy_key")

async def get_stock_data_finnhub(symbol: str):
    """Finnhub API ile hisse verisi çek"""
    if not FINNHUB_API_KEY or FINNHUB_API_KEY == "dummy_key":
        return None
    
    try:
        # Finnhub BIST hisseleri için "IS" eklenmesi gerekiyor
        finnhub_symbol = f"{symbol}.IS"
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            # 1. Güncel fiyat
            quote_url = f"https://finnhub.io/api/v1/quote?symbol={finnhub_symbol}&token={FINNHUB_API_KEY}"
            quote_res = await client.get(quote_url)
            quote_data = quote_res.json()
            
            if quote_res.status_code != 200:
                return None
            
            # 2. Şirket bilgileri
            profile_url = f"https://finnhub.io/api/v1/stock/profile2?symbol={finnhub_symbol}&token={FINNHUB_API_KEY}"
            profile_res = await client.get(profile_url)
            profile_data = profile_res.json() if profile_res.status_code == 200 else {}
            
            # Veriyi düzenle
            return {
                "symbol": symbol,
                "name": profile_data.get("name", BIST_STOCKS.get(symbol, symbol)),
                "price": quote_data.get("c", 0),  # Current price
                "change": quote_data.get("dp", 0),  # Percent change
                "high": quote_data.get("h", 0),  # Day high
                "low": quote_data.get("l", 0),  # Day low
                "open": quote_data.get("o", 0),  # Open price
                "volume": quote_data.get("v", 0),  # Volume
                "market_cap": profile_data.get("marketCapitalization", 0),
                "currency": "TRY",
                "source": "Finnhub"
            }
    except Exception as e:
        print(f"Finnhub hatası ({symbol}): {e}")
        return None

async def get_stock_data_alphavantage(symbol: str):
    """Alpha Vantage API ile hisse verisi çek (alternatif)"""
    # Alpha Vantage için ücretsiz API anahtarı alınabilir
    # https://www.alphavantage.co/support/#api-key
    ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_KEY", "")
    
    if not ALPHA_VANTAGE_KEY:
        return None
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}.IS&apikey={ALPHA_VANTAGE_KEY}"
            res = await client.get(url)
            data = res.json()
            
            if "Global Quote" not in data:
                return None
            
            quote = data["Global Quote"]
            return {
                "symbol": symbol,
                "name": BIST_STOCKS.get(symbol, symbol),
                "price": float(quote.get("05. price", 0)),
                "change": float(quote.get("10. change percent", "0%").replace("%", "")),
                "high": float(quote.get("03. high", 0)),
                "low": float(quote.get("04. low", 0)),
                "open": float(quote.get("02. open", 0)),
                "volume": int(quote.get("06. volume", 0)),
                "currency": "TRY",
                "source": "Alpha Vantage"
            }
    except Exception as e:
        print(f"Alpha Vantage hatası ({symbol}): {e}")
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
    """Hisse detayını getir - Finnhub veya Alpha Vantage ile"""
    
    symbol = symbol.upper()
    
    if symbol not in BIST_STOCKS:
        return {"error": f"{symbol} BIST listesinde bulunamadı"}
    
    # 1. Finnhub dene
    data = await get_stock_data_finnhub(symbol)
    
    # 2. Finnhub olmazsa Alpha Vantage dene
    if data is None:
        data = await get_stock_data_alphavantage(symbol)
    
    # 3. Hiçbiri çalışmazsa örnek veri döndür (gösterim için)
    if data is None or data.get("price", 0) == 0:
        # Hata mesajı
        return {
            "error": f"{symbol} için veri alınamıyor.",
            "message": "Lütfen daha sonra tekrar deneyin.",
            "hint": "Finnhub ücretsiz API anahtarı almak için: https://finnhub.io/register"
        }
    
    return data

@app.get("/api/stock/{symbol}/history")
async def get_stock_history(symbol: str):
    """Hisse geçmiş verileri (sadece Finnhub ile)"""
    if not FINNHUB_API_KEY or FINNHUB_API_KEY == "dummy_key":
        return {"error": "Finnhub API anahtarı gerekli"}
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Son 6 aylık veri
            url = f"https://finnhub.io/api/v1/stock/candle?symbol={symbol}.IS&resolution=D&count=180&token={FINNHUB_API_KEY}"
            res = await client.get(url)
            data = res.json()
            
            if "c" not in data or data.get("s") != "ok":
                return {"error": "Geçmiş veri alınamadı"}
            
            # Finnhub'dan gelen veriyi düzenle
            dates = [datetime.fromtimestamp(t).strftime("%Y-%m-%d") for t in data["t"]]
            
            return {
                "symbol": symbol,
                "dates": dates,
                "prices": data["c"],
                "volumes": data.get("v", [])
            }
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/chat")
async def chat(request: dict):
    """AI Asistanı (Gemini)"""
    if not GEMINI_API_KEY:
        return {"reply": "API anahtarı eksik"}
    
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={GEMINI_API_KEY}"
        payload = {"contents": [{"parts": [{"text": request.get("message", "")}]}]}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=30.0)
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
