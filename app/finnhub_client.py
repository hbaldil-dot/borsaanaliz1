# app/finnhub_client.py
import os
import requests
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class FinnhubClient:
    def __init__(self):
        self.api_key = os.getenv("FINNHUB_API_KEY")
        self.base_url = "https://finnhub.io/api/v1"
        
        if not self.api_key:
            logger.warning("⚠️ FINNHUB_API_KEY bulunamadı")
    
    def get_company_profile(self, symbol: str) -> Dict:
        """Şirket profil bilgileri"""
        if not self.api_key:
            return {}
        
        try:
            response = requests.get(
                f"{self.base_url}/stock/profile2",
                params={
                    "symbol": symbol.replace(".IS", ""),
                    "token": self.api_key
                }
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Finnhub profil hatası: {response.status_code}")
                return {}
        except Exception as e:
            logger.error(f"Finnhub profil hatası: {e}")
            return {}
    
    def get_recommendation(self, symbol: str) -> List[Dict]:
        """Analist tavsiyeleri"""
        if not self.api_key:
            return []
        
        try:
            response = requests.get(
                f"{self.base_url}/stock/recommendation",
                params={
                    "symbol": symbol.replace(".IS", ""),
                    "token": self.api_key
                }
            )
            
            if response.status_code == 200:
                return response.json()[:5]  # Son 5 tavsiye
            else:
                return []
        except Exception as e:
            logger.error(f"Finnhub tavsiye hatası: {e}")
            return []
    
    def get_earnings(self, symbol: str) -> List[Dict]:
        """Kazanç raporları"""
        if not self.api_key:
            return []
        
        try:
            response = requests.get(
                f"{self.base_url}/stock/earnings",
                params={
                    "symbol": symbol.replace(".IS", ""),
                    "token": self.api_key
                }
            )
            
            if response.status_code == 200:
                return response.json()[:4]  # Son 4 çeyrek
            else:
                return []
        except Exception as e:
            logger.error(f"Finnhub kazanç hatası: {e}")
            return []
