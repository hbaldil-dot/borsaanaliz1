"""
BIST Screener - Sade ve Çalışan Versiyon
"""

import os
import asyncio
import httpx
import yfinance as yf
from datetime import datetime
from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# APP BAŞLATMA
# ============================================================

app = FastAPI(title="BIST Screener", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# DEĞİŞKENLER
# ============================================================

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MONGO_URI = os.getenv("MONGODB_URI")

# ============================================================
# MODELLER
# ============================================================

class ChatRequest(BaseModel):
    user_id: str
    message: str

# ============================================================
# BIST HİSSE LİSTESİ (GÜNCEL)
# ============================================================

BIST_STOCKS = [
    "AEFES", "AKBNK", "AKSA", "ALARK", "ARCLK", "ASELS", "BIMAS", "BRSAN",
    "CCOLA", "DOAS", "DOHOL", "ECILC", "ENJSA", "ENKAI", "EREGL", "FROTO",
    "GARAN", "GUBRF", "HALKB", "ISCTR", "KARSN", "KCHOL", "KRDMD", "MAVI",
    "MGROS", "MPARK", "ODAS", "OTKAR", "OYAKC", "PETKM", "PGSUS", "SAHOL",
    "SASA", "SISE", "TAVHL", "TCELL", "THYAO", "TKFEN", "TOASO", "TSKB",
    "TTKOM", "TTRAK", "TUPRS", "VAKBN", "VESTL", "YKBNK", "ZOREN"
]

# ============================================================
# API ENDPOINTLERİ
# ============================================================

import re

@app.get("/api/stocks/live")
async def get_live_stocks():
    """Canlı BIST hisse listesini çek"""
    try:
        url = "https://www.kap.org.tr/tr/api/dis/bist-sirketler"
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.get(url)
            if res.status_code == 200:
                data = res.json()
                symbols = [item.get("kod") for item in data if item.get("kod")]
                symbols = [s.strip().upper() for s in symbols if s and len(s) >= 3]
                return {"stocks": sorted(list(set(symbols)))}
    except Exception as e:
        return {"error": str(e)}

@app.get("/")
async def home():
    """Ana sayfa"""
    return FileResponse("index.html")

@app.get("/api/stocks")
async def get_stocks():
    """Tüm BIST hisselerini listele"""
    return {"stocks": BIST_STOCKS}

@app.get("/api/stock/{symbol}")
async def get_stock(symbol: str):
    """Hisse detayını getir"""
    try:
        ticker = yf.Ticker(f"{symbol}.IS")
        
        # Önce bilgileri al
        info = ticker.info
        
        # Eğer info boşsa veya hata varsa
        if not info or 'symbol' not in info:
            return {"error": f"{symbol} için veri bulunamadı"}
        
        # Tarihsel veriyi al
        hist = ticker.history(period="2d")
        
        if hist.empty:
            # Alternatif: sadece info'dan fiyat almayı dene
            current_price = info.get('regularMarketPrice', info.get('currentPrice', 0))
            if current_price == 0:
                return {"error": f"{symbol} için fiyat verisi bulunamadı"}
            
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
        # Detaylı hata mesajı
        error_msg = str(e)
        if "No price data found" in error_msg:
            return {"error": f"{symbol} için veri bulunamadı"}
        return {"error": error_msg}

@app.post("/api/chat")
async def chat(request: ChatRequest):
    """AI Asistanı (Gemini)"""
    if not GEMINI_API_KEY:
        return {"reply": "API anahtarı eksik"}
    
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={GEMINI_API_KEY}"
        payload = {"contents": [{"parts": [{"text": request.message}]}]}
        
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
# UYGULAMA BAŞLATMA
# ============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
