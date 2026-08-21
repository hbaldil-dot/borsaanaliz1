import os
import httpx
import yfinance as yf
from datetime import date
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient

app = FastAPI()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MONGO_URI = os.getenv("MONGODB_URI")

# Günlük Önbellek (Cache) Değişkenleri
CACHED_STOCK_LIST = []
LAST_UPDATE_DATE = None

# Varsayılan Popüler BIST Hisseleri
BIST_ALL_STOCKS = [
    "AKBNK", "ALARK", "ARCLK", "ASELS", "BIMAS", "BRSAN", "DOAS", "EKGYO",
    "ENKAI", "EREGL", "FROTO", "GARAN", "HEKTS", "ISCTR", "KCHOL", "KONTR",
    "KOZAL", "KRDMD", "MGROS", "MIATK", "ODAS", "PETKM", "PGSUS", "SAHOL",
    "SASA", "SISE", "TCELL", "THYAO", "TOASO", "TUPRS", "VAKBN", "YKBNK"
]

class ChatRequest(BaseModel):
    user_id: str
    message: str

def get_daily_stock_list():
    """Hisse listesini günde sadece 1 defa günceller"""
    global CACHED_STOCK_LIST, LAST_UPDATE_DATE
    today = date.today()

    if LAST_UPDATE_DATE != today or not CACHED_STOCK_LIST:
        # İleride dinamik bir API entegre edilse bile burada önbelleğe alınır
        CACHED_STOCK_LIST = sorted(BIST_ALL_STOCKS)
        LAST_UPDATE_DATE = today
        print(f"[{today}] BIST Hisse listesi günlük olarak güncellendi.")

    return CACHED_STOCK_LIST

@app.get("/api/stocks/list")
async def get_stock_list():
    """Ön yüze güncel hisse listesini döndürür"""
    stocks = get_daily_stock_list()
    return {"stocks": stocks}

@app.get("/api/stock/{symbol}")
async def get_stock_info(symbol: str):
    try:
        ticker_symbol = f"{symbol.upper()}.IS" if not symbol.endswith(".IS") else symbol.upper()
        ticker = yf.Ticker(ticker_symbol)
        
        history = ticker.history(period="1d")
        if history.empty:
            return {"error": "Hisse verisi bulunamadı."}
        
        current_price = history['Close'].iloc[-1]
        
        financials = ticker.financials
        profit_data = {}
        
        if financials is not None and not financials.empty:
            if 'Net Income' in financials.index:
                net_incomes = financials.loc['Net Income']
                for d, val in net_incomes.items():
                    year = str(d.year)
                    profit_data[year] = f"{val / 1_000_000:,.2f} M TL"
        
        return {
            "symbol": symbol.upper(),
            "price": f"{current_price:.2f} TL",
            "profits": profit_data if profit_data else "Bilanço verisi çekilemedi"
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
