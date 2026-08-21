"""
BIST Screener - Çoklu Veri Kaynağı (Yedekli)
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
}

# ============================================================
# 🌐 VERİ KAYNAKLARI (Yedekli)
# ============================================================

async def get_stock_data_twelvedata(symbol):
    """Twelve Data API"""
    api_key = os.getenv("TWELVEDATA_API_KEY")
    if not api_key:
        return None
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            url = f"https://api.twelvedata.com/quote?symbol={symbol}.IS&apikey={api_key}"
            res = await client.get(url)
            data = res.json()
            
            if "price" in data:
                return {
                    "symbol": symbol,
                    "name": BIST_STOCKS.get(symbol, symbol),
                    "price": float(data.get("price", 0)),
                    "change": float(data.get("percent_change", 0)),
                    "high": float(data.get("high", 0)),
                    "low": float(data.get("low", 0)),
                    "open": float(data.get("open", 0)),
                    "volume": int(data.get("volume", 0)),
                    "currency": "TRY",
                    "source": "Twelve Data"
                }
    except Exception as e:
        print(f"Twelve Data hatası ({symbol}): {e}")
    return None

async def get_stock_data_alphavantage(symbol):
    """Alpha Vantage API"""
    api_key = os.getenv("ALPHA_VANTAGE_KEY")
    if not api_key:
        return None
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}.IS&apikey={api_key}"
            res = await client.get(url)
            data = res.json()
            
            if "Global Quote" in data:
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

async def get_stock_data_yahoo(symbol):
    """Yahoo Finance (son çare)"""
    try:
        import yfinance as yf
        ticker = yf.Ticker(f"{symbol}.IS")
        hist = ticker.history(period="1d")
        
        if not hist.empty:
            return {
                "symbol": symbol,
                "name": BIST_STOCKS.get(symbol, symbol),
                "price": float(hist['Close'].iloc[-1]),
                "change": 0,
                "high": float(hist['High'].iloc[-1]),
                "low": float(hist['Low'].iloc[-1]),
                "open": float(hist['Open'].iloc[-1]),
                "volume": int(hist['Volume'].iloc[-1]),
                "currency": "TRY",
                "source": "Yahoo Finance"
            }
    except Exception as e:
        print(f"Yahoo hatası ({symbol}): {e}")
    return None

async def get_stock_data_mock(symbol):
    """Örnek veri (API yoksa gösterim için)"""
    import random
    return {
        "symbol": symbol,
        "name": BIST_STOCKS.get(symbol, symbol),
        "price": round(random.uniform(50, 500), 2),
        "change": round(random.uniform(-5, 5), 2),
        "high": 0,
        "low": 0,
        "open": 0,
        "volume": random.randint(100000, 5000000),
        "currency": "TRY",
        "source": "Demo Veri"
    }

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
    """Hisse detayını getir - Çoklu kaynak"""
    
    symbol = symbol.upper()
    
    if symbol not in BIST_STOCKS:
        return {"error": f"{symbol} BIST listesinde bulunamadı"}
    
    # 🔄 SIRALI OLARAK DENE
    data = None
    
    # 1. Twelve Data
    data = await get_stock_data_twelvedata(symbol)
    if data and data.get("price", 0) > 0:
        return data
    
    # 2. Alpha Vantage
    data = await get_stock_data_alphavantage(symbol)
    if data and data.get("price", 0) > 0:
        return data
    
    # 3. Yahoo Finance
    data = await get_stock_data_yahoo(symbol)
    if data and data.get("price", 0) > 0:
        return data
    
    # 4. Demo Veri (API yoksa gösterim için)
    data = await get_stock_data_mock(symbol)
    
    # 🔔 Uyarı mesajı ile birlikte demo veri döndür
    return {
        **data,
        "warning": "⚠️ Gerçek veri alınamadı, demo veri gösteriliyor.",
        "hint": "API anahtarı eklemek için: Render Dashboard → Environment Variables"
    }

@app.get("/api/stock/{symbol}/history")
async def get_stock_history(symbol: str):
    """Hisse geçmiş verileri"""
    # Örnek veri
    import random
    dates = []
    prices = []
    for i in range(30, 0, -1):
        dates.append(f"2024-{i:02d}-01")
        prices.append(random.uniform(50, 500))
    
    return {
        "symbol": symbol.upper(),
        "dates": dates,
        "prices": prices,
        "source": "Demo Veri"
    }

@app.post("/api/chat")
async def chat(request: dict):
    """AI Asistanı (Gemini)"""
    if not GEMINI_API_KEY:
        return {"reply": "API anahtarı eksik. Render Dashboard'a GEMINI_API_KEY ekleyin."}
    
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
