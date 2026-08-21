"""
BIST Screener - Cache ve Rate Limit Korumalı
"""

import os
import time
import asyncio
import httpx
import yfinance as yf
from datetime import datetime, timedelta
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
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
# 📦 ÖNBELKEK (CACHE) SİSTEMİ
# ============================================================

class StockCache:
    def __init__(self):
        self.data = {}
        self.timestamps = {}
        self.ttl = 300  # 5 dakika
    
    def get(self, symbol):
        """Önbellekten veri al"""
        if symbol in self.data:
            if datetime.now() - self.timestamps[symbol] < timedelta(seconds=self.ttl):
                return self.data[symbol]
        return None
    
    def set(self, symbol, data):
        """Önbelleğe veri ekle"""
        self.data[symbol] = data
        self.timestamps[symbol] = datetime.now()
    
    def clear(self):
        """Önbelleği temizle"""
        self.data.clear()
        self.timestamps.clear()

stock_cache = StockCache()

# ============================================================
# 📊 BIST HİSSE LİSTESİ
# ============================================================

BIST_STOCKS = [
    "AEFES", "AKBNK", "AKSA", "ALARK", "ARCLK", "ASELS", "BIMAS", "BRSAN",
    "CCOLA", "DOAS", "DOHOL", "ECILC", "ENJSA", "ENKAI", "EREGL", "FROTO",
    "GARAN", "GUBRF", "HALKB", "ISCTR", "KCHOL", "KRDMD", "MAVI",
    "MGROS", "MPARK", "ODAS", "OTKAR", "OYAKC", "PETKM", "PGSUS", "SAHOL",
    "SASA", "SISE", "TAVHL", "TCELL", "THYAO", "TKFEN", "TOASO", "TSKB",
    "TTKOM", "TTRAK", "TUPRS", "VAKBN", "VESTL", "YKBNK"
]

# ============================================================
# 🔧 YARDIMCI FONKSİYONLAR (Rate Limit Korumalı)
# ============================================================

def safe_get_stock(symbol):
    """Rate limit hatasını yakala ve yeniden dene"""
    max_retries = 2
    for attempt in range(max_retries):
        try:
            ticker = yf.Ticker(f"{symbol}.IS")
            
            # Sadece info'yu al (history'den önce)
            info = ticker.info
            
            if not info or 'symbol' not in info:
                return None
            
            # Tarihsel veriyi al (2 gün)
            hist = ticker.history(period="2d")
            
            if hist.empty:
                # Sadece info'dan fiyat al
                current_price = info.get('regularMarketPrice', info.get('currentPrice', 0))
                if current_price == 0:
                    return None
                
                return {
                    "symbol": symbol.upper(),
                    "price": round(current_price, 2),
                    "change": 0,
                    "volume": info.get('volume', 0),
                    "market_cap": info.get('marketCap', 0),
                    "pe_ratio": info.get('trailingPE', 0),
                    "dividend_yield": info.get('dividendYield', 0)
                }
            
            current_price = hist['Close'].iloc[-1]
            prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else current_price
            change = ((current_price - prev_close) / prev_close) * 100 if prev_close > 0 else 0
            
            return {
                "symbol": symbol.upper(),
                "price": round(current_price, 2),
                "change": round(change, 2),
                "volume": int(hist['Volume'].iloc[-1]),
                "market_cap": info.get('marketCap', 0),
                "pe_ratio": info.get('trailingPE', 0),
                "dividend_yield": info.get('dividendYield', 0)
            }
            
        except Exception as e:
            error_msg = str(e)
            if "Too Many Requests" in error_msg:
                print(f"⚠️ Rate limit için {symbol} bekleniyor...")
                time.sleep(2)  # 2 saniye bekle
                continue
            return None
    
    return None

# ============================================================
# 🌐 API ENDPOINTLERİ
# ============================================================

@app.get("/")
async def home():
    return FileResponse("index.html")

@app.get("/api/stocks")
async def get_stocks():
    return {"stocks": BIST_STOCKS}

@app.get("/api/stock/{symbol}")
async def get_stock(symbol: str):
    """Hisse detayını getir (önbellekli)"""
    
    # Önbellekten kontrol et
    cached = stock_cache.get(symbol)
    if cached:
        return cached
    
    # Veriyi çek
    result = safe_get_stock(symbol)
    
    if result is None:
        return {"error": f"{symbol} için veri alınamıyor. Lütfen daha sonra tekrar deneyin."}
    
    # Önbelleğe ekle
    stock_cache.set(symbol, result)
    
    return result

@app.get("/api/stocks/all")
async def get_all_stocks():
    """Tüm hisselerin verilerini getir (toplu)"""
    results = {}
    errors = []
    
    for symbol in BIST_STOCKS[:10]:  # 10 hisse ile sınırlı, çok fazla istek atmamak için
        # Önbellekten kontrol et
        cached = stock_cache.get(symbol)
        if cached:
            results[symbol] = cached
            continue
        
        # Veriyi çek
        result = safe_get_stock(symbol)
        if result:
            stock_cache.set(symbol, result)
            results[symbol] = result
        else:
            errors.append(symbol)
        
        # Rate limit koruması
        await asyncio.sleep(0.5)
    
    return {
        "success": results,
        "errors": errors,
        "total": len(results)
    }

@app.post("/api/chat")
async def chat(request: dict):
    """AI Asistanı"""
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
