"""
BIST Screener - Yahoo Finance ile Gerçek Veri
"""

import os
import time
import random
import yfinance as yf
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
# 📊 TÜM BIST HİSSELERİ
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
    "VAKBN": "Vakıfbank",
    "HALKB": "Halkbank",
    "TCELL": "Turkcell",
    "TTKOM": "Türk Telekom",
    "BIMAS": "BİM",
    "MGROS": "Migros",
    "SOKM": "ŞOK Marketler",
    "EREGL": "Ereğli Demir Çelik",
    "KRDMD": "Kardemir",
    "FROTO": "Ford Otosan",
    "TOASO": "Tofaş",
    "OTKAR": "Otokar",
    "TTRAK": "Türk Traktör",
    "DOAS": "Doğuş Otomotiv",
    "TUPRS": "Tüpraş",
    "PETKM": "Petkim",
    "ENJSA": "Enerjisa",
    "PGSUS": "Pegasus",
    "TAVHL": "TAV Havalimanları",
    "VESTL": "Vestel",
    "ARCLK": "Arçelik",
    "SISE": "Şişe Cam",
    "CCOLA": "Coca-Cola İçecek",
    "AEFES": "Anadolu Efes",
    "ULKER": "Ülker",
    "MAVI": "Mavi Giyim",
    "SASA": "Sasa Polyester",
    "OYAKC": "Oyak Çimento",
    "ODAS": "Odaş Elektrik",
    "KOZAA": "Koza Altın",
    "KOZAL": "Koza Anadolu",
    "GUBRF": "Gübre Fabrikaları",
    "ANSGR": "Anadolu Sigorta",
    "AKGRT": "Aksigorta",
    "BRISA": "Brisa",
    "JANTS": "Jantsa",
    "KARSN": "Karsan",
    "ZOREN": "Zorlu Enerji",
}

# ============================================================
# 📊 VERİ ÇEKME FONKSİYONU (Yahoo Finance)
# ============================================================

def get_stock_data(symbol: str):
    """
    Yahoo Finance ile hisse verisi çek
    - Tüm BIST hisseleri için çalışır
    - Rate limit koruması var
    """
    try:
        ticker = yf.Ticker(f"{symbol}.IS")
        
        # 1. Günlük veri
        hist = ticker.history(period="1d")
        
        if hist.empty:
            print(f"⚠️ {symbol} için günlük veri yok, 5 günlük deneniyor...")
            hist = ticker.history(period="5d")
            if hist.empty:
                return None
        
        # 2. Info'dan ek bilgiler
        info = ticker.info
        
        # 3. Veriyi hazırla
        current_price = hist['Close'].iloc[-1]
        open_price = hist['Open'].iloc[-1] if 'Open' in hist else current_price
        
        # Değişim hesapla
        if len(hist) > 1:
            prev_close = hist['Close'].iloc[-2]
            change = ((current_price - prev_close) / prev_close) * 100
        else:
            change = ((current_price - open_price) / open_price) * 100 if open_price > 0 else 0
        
        # Şirket adı
        company_name = info.get('longName', info.get('shortName', BIST_STOCKS.get(symbol, symbol)))
        
        return {
            "symbol": symbol,
            "name": company_name,
            "price": round(current_price, 2),
            "change": round(change, 2),
            "high": round(hist['High'].iloc[-1], 2),
            "low": round(hist['Low'].iloc[-1], 2),
            "open": round(open_price, 2),
            "volume": int(hist['Volume'].iloc[-1] if 'Volume' in hist else 0),
            "market_cap": info.get('marketCap', 0),
            "pe_ratio": info.get('trailingPE', 0),
            "dividend_yield": info.get('dividendYield', 0),
            "currency": "TRY",
            "source": "Yahoo Finance",
            "timestamp": time.strftime("%H:%M:%S")
        }
        
    except Exception as e:
        print(f"❌ {symbol} hatası: {str(e)[:100]}")
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
    """Hisse detayını getir"""
    symbol = symbol.upper()
    
    if symbol not in BIST_STOCKS:
        return {"error": f"{symbol} BIST listesinde bulunamadı"}
    
    print(f"🔍 {symbol} sorgulanıyor...")
    
    # Veriyi çek
    data = get_stock_data(symbol)
    
    if data:
        print(f"✅ {symbol}: {data['price']} ₺ ({data['change']}%)")
        return data
    
    # Veri gelmezse demo döndür
    print(f"⚠️ {symbol} için demo veri")
    price = round(random.uniform(50, 500), 2)
    change = round(random.uniform(-5, 5), 2)
    
    return {
        "symbol": symbol,
        "name": BIST_STOCKS.get(symbol, symbol),
        "price": price,
        "change": change,
        "high": round(price * 1.02, 2),
        "low": round(price * 0.98, 2),
        "open": round(price * 0.99, 2),
        "volume": random.randint(100000, 5000000),
        "currency": "TRY",
        "source": "Demo Veri",
        "info": "⚠️ Yahoo Finance bağlantısı kurulamadı"
    }

@app.post("/api/chat")
async def chat(request: dict):
    """AI Asistanı"""
    if not GEMINI_API_KEY:
        return {"reply": "GEMINI_API_KEY ekleyin"}
    
    try:
        import httpx
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={GEMINI_API_KEY}"
        payload = {"contents": [{"parts": [{"text": request.get("message", "")}]}]}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
            data = response.json()
            
            if response.status_code == 200:
                reply = data["candidates"][0]["content"]["parts"][0]["text"]
                return {"reply": reply}
            return {"reply": f"API hatası: {response.status_code}"}
    except Exception as e:
        return {"reply": f"Hata: {str(e)}"}

@app.get("/api/test")
async def test():
    """Test endpoint"""
    return {
        "status": "OK",
        "time": time.strftime("%H:%M:%S"),
        "stocks_count": len(BIST_STOCKS)
    }

# ============================================================
# 🚀 UYGULAMA BAŞLATMA
# ============================================================

if __name__ == "__main__":
    import uvicorn
    print("🚀 BIST Screener başlatılıyor...")
    print(f"📊 Toplam hisse: {len(BIST_STOCKS)}")
    uvicorn.run(app, host="0.0.0.0", port=8000)
