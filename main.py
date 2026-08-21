"""
BIST Screener - Demo Veri ile Çalışan Versiyon
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

# ============================================================
# 📊 BIST HİSSE LİSTESİ
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
    """Hisse detayını getir (Demo veri)"""
    
    symbol = symbol.upper()
    
    if symbol not in BIST_STOCKS:
        return {"error": f"{symbol} BIST listesinde bulunamadı"}
    
    # 🎯 Demo veri oluştur
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
        "info": "⚠️ Gerçek veri alınamadığı için demo veri gösteriliyor"
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
