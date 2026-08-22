# app/main.py
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime
import uvicorn
import os
import logging

from app.data_collector import BISTDataCollector
from app.scoring_engine import ScoringEngine
from app.portfolio_optimizer import PortfolioOptimizer
from app.database import db

# Logging ayarları
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="BIST AI Analiz Motoru",
    description="Yahoo Finance + Finnhub destekli BIST hisse analiz ve portföy optimizasyonu",
    version="2.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS ayarları - Render için geniş izinler
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Singleton instance
collector = BISTDataCollector()
scorer = ScoringEngine(collector)
optimizer = PortfolioOptimizer(collector, scorer)

class PortfoyRequest(BaseModel):
    toplam_tutar: float = 100000
    risk_seviyesi: str = "orta"  # düşük, orta, yüksek

class ScanRequest(BaseModel):
    hisseler: Optional[List[str]] = None
    force_update: bool = False

@app.get("/")
async def root():
    """Ana sayfa"""
    return {
        "message": "BIST AI Analiz Motoru",
        "versiyon": "2.0",
        "veri_kaynagi": "Yahoo Finance + Finnhub",
        "environment": os.getenv("RENDER", "development"),
        "mongodb": "connected" if db.client else "disconnected",
        "endpoints": [
            "/api/hisseler",
            "/api/hisse/{kod}",
            "/api/scan",
            "/api/portfolio",
            "/api/mevduat",
            "/api/compare",
            "/api/update",
            "/api/saved_portfolios"
        ],
        "docs": "/docs"
    }

@app.get("/api/health")
async def health_check():
    """Sağlık kontrolü"""
    try:
        # MongoDB kontrolü
        db.client.server_info()
        mongo_status = "connected"
    except:
        mongo_status = "disconnected"
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "mongodb": mongo_status,
        "hisse_sayisi": len(collector.get_tum_hisseler())
    }

@app.get("/api/hisseler")
async def get_hisseler():
    """Tüm hisselerin listesi"""
    hisseler = collector.get_tum_hisseler()
    return {
        "hisseler": hisseler,
        "adet": len(hisseler),
        "tarih": datetime.now().isoformat()
    }

@app.get("/api/hisse/{kod}")
async def get_hisse_detay(kod: str, force_update: bool = False):
    """Hisse detayları"""
    # Önce veritabanından kontrol et
    if not force_update:
        cached = db.get_hisse(kod)
        if cached:
            # Cache'den dön
            return {
                "source": "cache",
                "data": cached,
                "tarih": datetime.now().isoformat()
            }
    
    # Yahoo Finance'den al
    veri = collector.get_hisse_verisi(kod, force_update)
    if not veri:
        raise HTTPException(status_code=404, detail="Hisse bulunamadı")
    
    skor = scorer.hisse_puanla(kod)
    bilanco = collector.get_bilanco(kod)
    
    # Veritabanına kaydet
    db.save_hisse({**veri, "skor": skor})
    if bilanco:
        db.save_bilanco(kod, bilanco)
    
    return {
        "source": "yahoo_finance",
        "kod": kod,
        "fiyat_verisi": veri,
        "skor": skor,
        "bilanco": bilanco,
        "tarih": datetime.now().isoformat()
    }

@app.post("/api/scan")
async def scan_hisseler(request: ScanRequest):
    """Hisse taraması yap"""
    tum_hisseler = request.hisseler or collector.get_tum_hisseler()
    sonuclar = []
    hata_hisseler = []
    
    for kod in tum_hisseler[:20]:  # Rate limiting için ilk 20
        try:
            veri = collector.get_hisse_verisi(kod, request.force_update)
            if veri:
                skor = scorer.hisse_puanla(kod)
                if skor:
                    sonuclar.append(skor)
                    db.save_hisse({
                        "kod": kod,
                        "veri": veri,
                        "skor": skor,
                        "tarih": datetime.now()
                    })
        except Exception as e:
            hata_hisseler.append({"kod": kod, "hata": str(e)})
            logger.error(f"❌ {kod} taranırken hata: {e}")
    
    sonuclar.sort(key=lambda x: x["toplam_skor"], reverse=True)
    
    return {
        "tarih": datetime.now().isoformat(),
        "toplam_hisse": len(sonuclar),
        "hata_hisseler": hata_hisseler,
        "ilk_20": sonuclar[:20],
        "ilk_5": sonuclar[:5]
    }

@app.post("/api/portfolio")
async def optimize_portfolio(request: PortfoyRequest):
    """Portföy optimizasyonu"""
    try:
        sonuc = optimizer.optimize(request.toplam_tutar, request.risk_seviyesi)
        
        # Sonucu kaydet
        db.save_portfoy({
            "request": request.dict(),
            "sonuc": sonuc,
            "tarih": datetime.now()
        })
        
        return sonuc
    except Exception as e:
        logger.error(f"❌ Portföy optimizasyon hatası: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/mevduat")
async def mevduat_hesapla(tutar: float = 100000, oran: float = 46, ay: int = 6):
    """Mevduat getirisi hesapla"""
    stopaj = 0.175
    brut_faiz = tutar * (oran / 100 / 12) * ay
    net_faiz = brut_faiz * (1 - stopaj)
    
    return {
        "anapara": tutar,
        "faiz_orani": oran,
        "vade_ay": ay,
        "brut_faiz": round(brut_faiz, 2),
        "stopaj": round(brut_faiz * stopaj, 2),
        "net_faiz": round(net_faiz, 2),
        "son_deger": round(tutar + net_faiz, 2),
        "net_getiri_yuzde": round((net_faiz / tutar) * 100, 2)
    }

@app.get("/api/compare")
async def compare_portfolio_vs_mevduat(tutar: float = 100000):
    """Hisse portföyü vs mevduat karşılaştırması"""
    # Portföy optimizasyonu
    portfoy = optimizer.optimize(tutar)
    
    # Mevduat
    mevduat = await mevduat_hesapla(tutar)
    
    return {
        "tarih": datetime.now().isoformat(),
        "portfoy": {
            "beklenen_deger": portfoy["beklenen_deger"],
            "beklenen_getiri": portfoy["beklenen_getiri"],
            "detay": portfoy["portfoy"]
        },
        "mevduat": {
            "son_deger": mevduat["son_deger"],
            "net_getiri_yuzde": mevduat["net_getiri_yuzde"]
        },
        "fark": {
            "tl": round(portfoy["beklenen_deger"] - mevduat["son_deger"], 2),
            "yuzde": round(
                ((portfoy["beklenen_deger"] - mevduat["son_deger"]) / mevduat["son_deger"]) * 100,
                2
            )
        }
    }

@app.post("/api/update")
async def update_all_data(background_tasks: BackgroundTasks):
    """Tüm verileri güncelle"""
    background_tasks.add_task(update_data_background)
    return {"status": "Veri güncelleme başlatıldı", "tarih": datetime.now().isoformat()}

@app.get("/api/saved_portfolios")
async def get_saved_portfolios(limit: int = 10):
    """Kaydedilmiş portföyleri getir"""
    return {
        "portfoyler": db.get_portfoyler(limit),
        "tarih": datetime.now().isoformat()
    }

@app.on_event("startup")
async def startup_event():
    """Uygulama başlarken"""
    logger.info("🚀 BIST AI Analiz Motoru başlatılıyor...")
    logger.info(f"📊 Toplam hisse: {len(collector.get_tum_hisseler())}")
    logger.info(f"🔗 MongoDB: {'Bağlı' if db.client else 'Bağlantı yok'}")
    
    # Environment'ı göster
    logger.info(f"🌍 Environment: {os.getenv('RENDER', 'development')}")
    logger.info(f"🔑 Finnhub API: {'Mevcut' if os.getenv('FINNHUB_API_KEY') else 'Yok'}")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=False if os.getenv("RENDER") else True
    )
