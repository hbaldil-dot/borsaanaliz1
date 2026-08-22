import os
import json
import google.generativeai as genai

# Gemini API Yapılandırması
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

SYSTEM_PROMPT = """
Aşağıdaki adımları sırasıyla uygulayarak Borsa İstanbul (BIST) pay piyasasında işlem gören tüm hisse senetleri üzerinde 3 aşamalı bir analiz gerçekleştir:

[AŞAMA 1: ELEME VE İLK 100 HİSSENİN BELİRLENMESİ]
1. 2026 Yılı Karlılığı: Net Kar > 0 olan şirketler.
2. Zirve/Fiyat Oranı: 12 Aylık En Yüksek Fiyat / Günlük Mevcut Fiyat oranı en yüksek olanlar.
3. USD Bazlı Ucuzluk: USD bazında geçmiş 3-5 yıllık ortalamalara göre belirgin iskonto içerenler.

[AŞAMA 2: DETAYLI ÇOKLU ANALİZ]
Belirlenen 100 hisse için Teknik Grafik, KAP Haberleri ve Çarpan Analizi uygula.

[AŞAMA 3: İLK 20 HİSSENİN SEÇİMİ VE PUANLANMASI]
En yüksek potansiyele sahip 20 hisseyi seç ve 100 üzerinden puanla.

[ÇIKTI FORMATI]
Yanıtı SADECE ve SADECE aşağıdaki JSON formatında ver, ekstra metin ekleme:
[
  {
    "hisse": "SAHOL",
    "fiyat": 90.15,
    "hedef_fiyat": 155.00,
    "potansiyel": "+%71.9",
    "direnc": "105/115",
    "puan": 89,
    "ozet": "Düşen trend kırılımı gerçekleşti, olumlu KAP akışı bekleniyor."
  }
]
"""

def tam_ai_analiz_yap():
    """Gemini API üzerinden tam prompt analizini çalıştırır."""
    if not GEMINI_API_KEY:
        return None
        
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(SYSTEM_PROMPT)
        
        # JSON temizleme ve dönüştürme
        text_data = response.text.replace("```json", "").replace("```", "").strip()
        sonuclar = json.loads(text_data)
        return sonuclar
    except Exception as e:
        print(f"AI Analiz Hatası: {e}")
        return None

def hisse_analiz_et(hisse_kodu: str):
    # Tekil çağrılar için yedek mantık
    return None
