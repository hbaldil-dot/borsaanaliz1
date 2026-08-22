# app/scoring_engine.py
import random
from typing import Dict
from app.data_collector import BISTDataCollector

class ScoringEngine:
    def __init__(self, collector: BISTDataCollector):
        self.collector = collector
    
    def hisse_puanla(self, kod: str) -> Dict:
        """Hisseyi 100 üzerinden puanla"""
        veri = self.collector.get_hisse_verisi(kod)
        if not veri:
            return None
        
        # Demo puanlama - gerçek hesaplama için geliştirilecek
        return {
            "kod": kod,
            "fiyat": veri.get("fiyat", 0),
            "hedef_fiyat": veri.get("hedef_fiyat", 0),
            "ucuzluk_skoru": random.randint(15, 25),
            "teknik_skoru": random.randint(20, 40),
            "kalite_skoru": random.randint(10, 20),
            "katalizor_skoru": random.randint(5, 15),
            "toplam_skor": random.randint(50, 100),
            "potansiyel_getiri": veri.get("potansiyel_getiri", 0)
        }
