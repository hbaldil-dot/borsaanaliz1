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

# Günlük Hafıza (Cache)
CACHED_STOCK_LIST = []
LAST_UPDATE_DATE = None

class ChatRequest(BaseModel):
    user_id: str
    message: str

async def fetch_live_bist_list():
    """BIST üzerindeki tüm aktif hisse kodlarını canlı olarak çeker."""
    url = "https://www.isyatirim.com.tr/tr-tr/analiz/hisse/Sayfalar/default.aspx"
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            res = await client.get(url)
            # Sayfa içeriğindeki .HEPSİ / .IS uzantılı BIST sembollerini yakalar
            raw_symbols = re.findall(r'data-value="([A-Z0-9]+)\.E"', res.text)
            if not raw_symbols:
                # Alternatif regex arama
                raw_symbols = re.findall(r'/hisse/([A-Z0-9]+)"', res.text)
            
            symbols = sorted(list(set(raw_symbols)))
            if symbols:
                return symbols
        except Exception as e:
            print(f"Canlı hisse listesi çekme hatası: {e}")
            
    # Eğer web scraping engellenirse yedek dinamik fallback
    return ["AKBNK", "ARCLK", "ASELS", "BIMAS", "EREGL", "FROTO", "GARAN", "KCHOL", "SASA", "THYAO", "TUPRS"]

async def get_daily_stock_list():
    """Günde sadece 1 kere listeyi günceller, gün boyu aynı listeyi kullanır."""
    global CACHED_STOCK_LIST, LAST_UPDATE_DATE
    today = date.today()

    # Liste hiç çekilmediyse veya gün değiştiyse canlı güncelle
    if LAST_UPDATE_DATE != today or not CACHED_STOCK_LIST:
        print(f"[{today}] Borsa İstanbul güncel hisse listesi internetten çekiliyor...")
        CACHED_STOCK_LIST = await fetch_live_bist_list()
        LAST_UPDATE_DATE = today
        print(f"[{today}] Toplam {len(CACHED_STOCK_LIST)} adet güncel BIST hissesi hafızaya alındı.")

    return CACHED_STOCK_LIST

@app.get("/api/stocks/list")
async def get_stock_list():
    """Günün güncel hisse listesini döndürür"""
    stocks = await get_daily_stock_list()
    return {"stocks": stocks}

@app.get("/api/stock/{symbol}")
async def get_stock_info(symbol: str):
    """Seçilen hisse tıklandığında anlık/15dk gecikmeli veriyi çeker"""
    try:
        ticker_symbol = f"{symbol.upper()}.IS" if not symbol.endswith(".IS") else symbol.upper()
        ticker = yf.Ticker(ticker_symbol)
        
        # 15 dk gecikmeli anlık fiyat verisi
        history = ticker.history(period="1d")
        if history.empty:
            return {"error": "Hisse verisi Yahoo Finance üzerinde bulunamadı."}
        
        current_price = history['Close'].iloc[-1]
        
        # Bilanço Kâr Verileri
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
