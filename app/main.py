# app/main.py
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, List
from datetime import datetime
import uvicorn
import asyncio

from app.data_collector import BISTDataCollector
from app.scoring_engine import ScoringEngine
from app.portfolio_optimizer import PortfolioOptimizer
from app.database import db

app = FastAPI(
    title="BIST AI Analiz Motoru",
    description="Yahoo Finance destekli BIST hisse analiz ve portföy optimizasyonu",
    version="2.0"
)

# CORS
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
    return {
        "message": "BIST AI Analiz Motoru",
        "versiyon": "2.0",
        "veri_kaynagi": "Yahoo Finance",
        "endpoints": [
            "/api/hisseler",
            "/api/hisse/{kod}",
            "/api/scan",
            "/api/portfolio",
            "/api/mevduat",
            "/api/compare",
            "/api/update"
        ]
    }

@app.get("/api/hisseler")
async def get_hisseler():
    """Tüm hisselerin listesi"""
    return {
        "hisseler": collector.get_tum_hisseler(),
        "adet": len(collector.get_tum_hisseler()),
        "tarih": datetime.now().isoformat()
    }

@app.get("/api/hisse/{kod}")
async def get_hisse_detay(kod: str, force_update: bool = False):
    """Hisse detayları"""
    veri = collector.get_hisse_verisi(kod, force_update)
    if not veri:
        raise HTTPException(status_code=404, detail="Hisse bulunamadı")
    
    skor = scorer.hisse_puanla(kod)
    bilanco = collector.get_bilanco(kod)
    
    # Teknik analiz
    hist = collector.get_historical_data(kod, period="6mo")
    from app.technical_analysis import TechnicalAnalysis
    teknik = TechnicalAnalysis.calculate_all_indicators(hist) if not hist.empty else {}
    
    return {
        "kod": kod,
        "fiyat_verisi": veri,
        "skor": skor,
        "bilanco": bilanco,
        "teknik": teknik,
        "tarih": datetime.now().isoformat()
    }

@app.post("/api/scan")
async def scan_hisseler(request: ScanRequest):
    """Hisse taraması yap"""
    tum_hisseler = request.hisseler or collector.get_tum_hisseler()
    sonuclar = []
    hata_hisseler = []
    
    for kod in tum_hisseler:
        try:
            # Veriyi güncelle
            veri = collector.get_hisse_verisi(kod, request.force_update)
            if veri:
                # Puanla
                skor = scorer.hisse_puanla(kod)
                if skor:
                    sonuclar.append(skor)
                    # Veritabanına kaydet
                    db.save_hisse({
                        "kod": kod,
                        "veri": veri,
                        "skor": skor,
                        "tarih": datetime.now()
                    })
        except Exception as e:
            hata_hisseler.append({"kod": kod, "hata": str(e)})
    
    # Sırala
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
        db.save_analiz_sonucu({
            "tip": "portfolio",
            "request": request.dict(),
            "sonuc": sonuc,
            "tarih": datetime.now()
        })
        
        return sonuc
    except Exception as e:
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

async def update_data_background():
    """Arka planda veri güncelleme"""
    hisseler = collector.get_tum_hisseler()
    for kod in hisseler:
        try:
            collector.get_hisse_verisi(kod, force_update=True)
            collector.get_bilanco(kod)
        except Exception as e:
            print(f"❌ {kod} güncellenirken hata: {e}")
        await asyncio.sleep(0.5)  # Rate limiting

@app.on_event("startup")
async def startup_event():
    """Uygulama başlarken ilk verileri getir"""
    print("🚀 BIST AI Analiz Motoru başlatılıyor...")
    print(f"📊 Toplam hisse: {len(collector.get_tum_hisseler())}")
    
    # İlk 5 hisseyi ön yükle
    for kod in ["SAHOL", "KCHOL", "ULKER", "FROTO", "PGSUS"]:
        try:
            collector.get_hisse_verisi(kod)
            print(f"✅ {kod} verisi yüklendi")
        except Exception as e:
            print(f"❌ {kod} yüklenirken hata: {e}")

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
