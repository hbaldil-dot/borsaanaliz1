import os
import json
import re
import google.generativeai as genai
from openai import OpenAI

# API Anahtarları
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# OpenAI İstemcisi
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# Gemini Yapılandırması
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

PROMPT_TEXT = """
Sen uzman bir BIST (Borsa İstanbul) hisse senedi analistisin.
Lütfen BIST'te işlem gören ve önümüzdeki dönemde yüksek potansiyele sahip EN İYİ 20 hisse senedini analiz et.

YAPIŞTIRILACAK YANIT SADECE VE SADECE AŞAĞIDAKİ JSON FORMATINDA OLMALIDIR (Başka hiçbir açıklama yazma):
[
  {
    "hisse": "THYAO",
    "fiyat": 305.5,
    "hedef": 420.0,
    "potansiyel": "%37.5",
    "puan": 92,
    "ozet": "Güçlü yolcu trafiği ve havayolu kârlılık beklentisi."
  }
]
"""

def json_temizle_ve_yukle(metin):
    """Yapay zekadan gelen metnin içindeki JSON yapısını çıkarır."""
    try:
        match = re.search(r'\[.*\]', metin, re.DOTALL)
        if match:
            json_str = match.group(0)
            return json.loads(json_str)
        return json.loads(metin)
    except Exception as e:
        print(f"JSON Ayrıştırma Hatası: {e}")
        return []

def gpt_analiz_yap():
    if not OPENAI_API_KEY:
        print("ChatGPT API anahtarı bulunamadı.")
        return []
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Sadece geçerli bir JSON dizisi yanıtı ver."},
                {"role": "user", "content": PROMPT_TEXT}
            ],
            temperature=0.7
        )
        icerik = response.choices[0].message.content
        return json_temizle_ve_yukle(icerik)
    except Exception as e:
        print(f"ChatGPT API Hatası: {e}")
        return []

def gemini_analiz_yap():
    if not GEMINI_API_KEY:
        print("Gemini API anahtarı bulunamadı.")
        return []
    
    # Güncel API modelleri sırasıyla denenir
    modeller = ['gemini-3.6-flash', 'gemini-1.5-flash-8b', 'gemini-2.0-flash-exp']
    
    for model_adi in modeller:
        try:
            model = genai.GenerativeModel(model_adi)
            response = model.generate_content(PROMPT_TEXT)
            sonuc = json_temizle_ve_yukle(response.text)
            if sonuc:
                return sonuc
        except Exception as e:
            print(f"Gemini ({model_adi}) Hatası: {e}")
            continue
            
    return []

def cift_ai_analiz_yap():
    print("Canlı AI Analiz Taraması Başlatıldı...")
    gpt_liste = gpt_analiz_yap()
    gemini_liste = gemini_analiz_yap()

    ortak_liste = []
    gemini_dict = {item.get('hisse'): item for item in gemini_liste if isinstance(item, dict) and 'hisse' in item}

    for g_item in gpt_liste:
        if isinstance(g_item, dict) and 'hisse' in g_item:
            hisse_kodu = g_item['hisse']
            if hisse_kodu in gemini_dict:
                m_item = gemini_dict[hisse_kodu]
                try:
                    gpt_puan = int(g_item.get('puan', 0))
                    gemini_puan = int(m_item.get('puan', 0))
                    ort_puan = round((gpt_puan + gemini_puan) / 2, 1)
                except (ValueError, TypeError):
                    gpt_puan = g_item.get('puan', 0)
                    gemini_puan = m_item.get('puan', 0)
                    ort_puan = "-"

                ortak_liste.append({
                    "hisse": hisse_kodu,
                    "fiyat": g_item.get('fiyat', '-'),
                    "gpt_puan": gpt_puan,
                    "gemini_puan": gemini_puan,
                    "ort_puan": ort_puan,
                    "potansiyel": g_item.get('potansiyel', '-'),
                    "ozet": f"GPT Notu: {g_item.get('ozet', '')} | Gemini Notu: {m_item.get('ozet', '')}"
                })

    ortak_liste.sort(key=lambda x: x['ort_puan'] if isinstance(x['ort_puan'], (int, float)) else 0, reverse=True)

    return {
        "gpt": gpt_liste,
        "gemini": gemini_liste,
        "ortak": ortak_liste
    }
