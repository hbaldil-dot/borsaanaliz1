# app/portfolio_optimizer.py
from typing import Dict, List
from app.data_collector import BISTDataCollector
from app.scoring_engine import ScoringEngine

class PortfolioOptimizer:
    def __init__(self, collector: BISTDataCollector, scorer: ScoringEngine):
        self.collector = collector
        self.scorer = scorer
    
    def optimize(self, toplam_tutar: float, risk_seviyesi: str = "orta") -> Dict:
        """Portföy optimizasyonu"""
        tum_hisseler = self.collector.get_tum_hisseler()
        puanli_hisseler = []
        
        for kod in tum_hisseler[:10]:  # İlk 10
            skor = self.scorer.hisse_puanla(kod)
            if skor:
                puanli_hisseler.append(skor)
        
        puanli_hisseler.sort(key=lambda x: x["toplam_skor"], reverse=True)
        ilk5 = puanli_hisseler[:5]
        
        # Ağırlıklar
        agirliklar = {
            "SAHOL": 0.25,
            "KCHOL": 0.22,
            "ULKER": 0.20,
            "FROTO": 0.18,
            "PGSUS": 0.15
        }
        
        portfoy = []
        for hisse in ilk5:
            kod = hisse["kod"]
            agirlik = agirliklar.get(kod, 0.20)
            tutar = toplam_tutar * agirlik
            
            portfoy.append({
                "kod": kod,
                "fiyat": hisse["fiyat"],
                "hedef_fiyat": hisse["hedef_fiyat"],
                "agirlik": agirlik,
                "tutar": tutar,
                "adet": int(tutar / hisse["fiyat"]) if hisse["fiyat"] > 0 else 0,
                "potansiyel_getiri": hisse["potansiyel_getiri"],
                "toplam_skor": hisse["toplam_skor"]
            })
        
        getiri = sum([p["agirlik"] * p["potansiyel_getiri"] / 100 for p in portfoy])
        
        return {
            "portfoy": portfoy,
            "toplam_tutar": toplam_tutar,
            "beklenen_getiri": getiri * 100,
            "beklenen_deger": toplam_tutar * (1 + getiri)
        }
