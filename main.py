"""
BIST Screener - Yahoo Finance ile Cache + Rate Limit Korumalı
"""

import os
import time
import random
from datetime import datetime, timedelta
import yfinance as yf
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="BIST Screener", version="2.0")

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
# 📊 BIST HİSSELERİ
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
}

# ============================================================
# 📈 YAHOO FINANCE VERİ ÇEKME (RATE LIMIT KORUMALI)
# ============================================================

# Son istek zamanını takip et
last_request_time = 0
min_request_interval = 2  # Her istek arasında 2 saniye bekle

def get_stock_data(symbol: str):
    """
    Yahoo Finance ile hisse verisi çek - Rate limit korumalı
    """
    global last_request_time
    
    # 1️⃣ Önbellekten kontrol et
    cached = stock_cache.get(symbol)
    if cached:
        print(f"📦 {symbol} önbellekten geldi")
        return cached
    
    # 2️⃣ Rate limit koruması
    current_time = time.time()
    time_since_last = current_time - last_request_time
    if time_since_last < min_request_interval:
        wait_time = min_request_interval - time_since_last
        print(f"⏳ Rate limit için {wait_time:.1f} saniye bekleniyor...")
        time.sleep(wait_time)
    
    try:
        last_request_time = time.time()
        
        ticker = yf.Ticker(f"{symbol}.IS")
        
        # Info al (tek istek)
        info = ticker.info
        
        if not info or 'regularMarketPrice' not in info:
            # History ile dene
            hist = ticker.history(period="2d")
            if hist.empty:
                return None
            
            current_price = hist['Close'].iloc[-1]
            open_price = hist['Open'].iloc[-1]
            high_price = hist['High'].iloc[-1]
            low_price = hist['Low'].iloc[-1]
            volume = hist['Volume'].iloc[-1] if 'Volume' in hist else 0
            
            if len(hist) > 1:
                prev_close = hist['Close'].iloc[-2]
                change = ((current_price - prev_close) / prev_close) * 100
            else:
                change = 0
            
            data = {
                "symbol": symbol,
                "name": BIST_STOCKS.get(symbol, symbol),
                "price": round(float(current_price), 2),
                "change": round(float(change), 2),
                "high": round(float(high_price), 2),
                "low": round(float(low_price), 2),
                "open": round(float(open_price), 2),
                "volume": int(volume),
                "source": "Yahoo Finance",
                "timestamp": time.strftime("%H:%M:%S")
            }
            
            # Önbelleğe ekle
            stock_cache.set(symbol, data)
            return data
        
        # Info'dan veri al
        current_price = info.get('regularMarketPrice', 0)
        if current_price == 0:
            current_price = info.get('currentPrice', 0)
        
        if current_price == 0:
            return None
        
        change = info.get('regularMarketChangePercent', 0)
        if change == 0:
            change = info.get('changePercent', 0)
        
        name = info.get('longName', info.get('shortName', BIST_STOCKS.get(symbol, symbol)))
        
        data = {
            "symbol": symbol,
            "name": name,
            "price": round(float(current_price), 2),
            "change": round(float(change), 2),
            "high": round(float(info.get('regularMarketDayHigh', info.get('dayHigh', current_price))), 2),
            "low": round(float(info.get('regularMarketDayLow', info.get('dayLow', current_price))), 2),
            "open": round(float(info.get('regularMarketOpen', info.get('open', current_price))), 2),
            "volume": int(info.get('regularMarketVolume', info.get('volume', 0))),
            "source": "Yahoo Finance",
            "timestamp": time.strftime("%H:%M:%S")
        }
        
        # Önbelleğe ekle
        stock_cache.set(symbol, data)
        print(f"✅ {symbol}: {data['price']} ₺ (kaydedildi)")
        return data
        
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "Too Many Requests" in error_msg:
            print(f"⚠️ Rate limit aşıldı ({symbol}), 5 saniye bekleniyor...")
            time.sleep(5)
            return None
        print(f"❌ {symbol} hatası: {error_msg[:100]}")
        return None

# ============================================================
# 🧪 TEST ENDPOINT
# ============================================================

@app.get("/api/test/{symbol}")
async def test_stock(symbol: str):
    """Test endpoint"""
    symbol = symbol.upper()
    try:
        ticker = yf.Ticker(f"{symbol}.IS")
        info = ticker.info
        
        return {
            "symbol": symbol,
            "price": info.get('regularMarketPrice', 'yok'),
            "info_keys": list(info.keys())[:10] if info else [],
            "has_data": bool(info and info.get('regularMarketPrice'))
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/cache/clear")
async def clear_cache():
    """Önbelleği temizle"""
    stock_cache.clear()
    return {"status": "Cache cleared"}

# ============================================================
# 🌐 API ENDPOINTLERİ
# ============================================================

@app.get("/")
async def home():
    return FileResponse("index.html")

@app.get("/api/stocks")
async def get_stocks():
    return {"stocks": list(BIST_STOCKS.keys())}

@app.get("/api/stock/{symbol}")
async def get_stock(symbol: str):
    symbol = symbol.upper()
    
    if symbol not in BIST_STOCKS:
        return {"error": f"{symbol} bulunamadı"}
    
    # Veriyi çek (önbellekli)
    data = get_stock_data(symbol)
    
    if data:
        return data
    
    # Veri gelmezse demo
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
        "source": "Demo Veri",
        "timestamp": time.strftime("%H:%M:%S"),
        "info": "⚠️ Yahoo Finance rate limit aşıldı, demo veri gösteriliyor"
    }

@app.post("/api/chat")
async def chat(request: dict):
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
                return {"reply": data["candidates"][0]["content"]["parts"][0]["text"]}
            return {"reply": f"API hatası: {response.status_code}"}
    except Exception as e:
        return {"reply": f"Hata: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    print("🚀 BIST Screener V2 başlatılıyor...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
