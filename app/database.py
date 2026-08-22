# app/database.py
import os
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from dotenv import load_dotenv
import logging

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MongoDB:
    def __init__(self):
        try:
            # Render'daki environment variable'ları kullan
            mongodb_uri = os.getenv("MONGODB_URI")
            
            if not mongodb_uri:
                # Fallback olarak parçalardan oluştur
                username = os.getenv("MONGODB_USERNAME")
                password = os.getenv("MONGODB_PASSWORD")
                if username and password:
                    mongodb_uri = f"mongodb+srv://{username}:{password}@whzghn.mongodb.net/?retryWrites=true&w=majority"
            
            logger.info(f"MongoDB URI: {mongodb_uri[:30]}...")  # Güvenlik için kısalt
            
            self.client = MongoClient(
                mongodb_uri,
                serverSelectionTimeoutMS=5000,
                maxPoolSize=10
            )
            
            # Bağlantıyı test et
            self.client.server_info()
            logger.info("✅ MongoDB bağlantısı başarılı")
            
            self.db = self.client["borsaanalizi_db"]
            self.hisseler = self.db["hisseler"]
            self.bilanco = self.db["bilanco"]
            self.kap = self.db["kap_bildirimleri"]
            self.sonuclar = self.db["analiz_sonuclari"]
            self.portfoy = self.db["portfoyler"]
            
            # Index'ler oluştur
            self._create_indexes()
            
        except ConnectionFailure as e:
            logger.error(f"❌ MongoDB bağlantı hatası: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ MongoDB başlatma hatası: {e}")
            raise
    
    def _create_indexes(self):
        """Veritabanı index'lerini oluştur"""
        try:
            self.hisseler.create_index("kod", unique=True)
            self.hisseler.create_index("tarih")
            self.bilanco.create_index("kod", unique=True)
            self.kap.create_index("hisse_kod")
            self.sonuclar.create_index([("tarih", -1)])
            self.portfoy.create_index([("tarih", -1)])
            logger.info("✅ MongoDB index'leri oluşturuldu")
        except Exception as e:
            logger.warning(f"⚠️ Index oluşturma hatası: {e}")
    
    def save_hisse(self, veri: dict):
        """Hisse verisini kaydet"""
        try:
            self.hisseler.update_one(
                {"kod": veri["kod"]},
                {"$set": veri},
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"❌ Hisse kaydedilirken hata: {e}")
            return False
    
    def get_hisse(self, kod: str) -> dict:
        """Hisse verisini getir"""
        try:
            return self.hisseler.find_one({"kod": kod})
        except Exception as e:
            logger.error(f"❌ Hisse getirilirken hata: {e}")
            return None
    
    def save_bilanco(self, kod: str, bilanco: dict):
        """Bilanço verisini kaydet"""
        try:
            bilanco["kod"] = kod
            self.bilanco.update_one(
                {"kod": kod},
                {"$set": bilanco},
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"❌ Bilanço kaydedilirken hata: {e}")
            return False
    
    def save_analiz_sonucu(self, sonuc: dict):
        """Analiz sonucunu kaydet"""
        try:
            sonuc["tarih"] = sonuc.get("tarih")
            self.sonuclar.insert_one(sonuc)
            return True
        except Exception as e:
            logger.error(f"❌ Analiz sonucu kaydedilirken hata: {e}")
            return False
    
    def get_son_analizler(self, limit: int = 10):
        """Son analiz sonuçlarını getir"""
        try:
            return list(self.sonuclar.find().sort("tarih", -1).limit(limit))
        except Exception as e:
            logger.error(f"❌ Son analizler getirilirken hata: {e}")
            return []
    
    def save_portfoy(self, portfoy: dict):
        """Portföyü kaydet"""
        try:
            portfoy["tarih"] = portfoy.get("tarih")
            self.portfoy.insert_one(portfoy)
            return True
        except Exception as e:
            logger.error(f"❌ Portföy kaydedilirken hata: {e}")
            return False
    
    def get_portfoyler(self, limit: int = 10):
        """Kaydedilmiş portföyleri getir"""
        try:
            return list(self.portfoy.find().sort("tarih", -1).limit(limit))
        except Exception as e:
            logger.error(f"❌ Portföyler getirilirken hata: {e}")
            return []
    
    def close(self):
        """Bağlantıyı kapat"""
        try:
            self.client.close()
            logger.info("✅ MongoDB bağlantısı kapatıldı")
        except Exception as e:
            logger.error(f"❌ Bağlantı kapatılırken hata: {e}")

# Singleton instance
db = MongoDB()
