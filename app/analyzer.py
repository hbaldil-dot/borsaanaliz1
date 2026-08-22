import os
import json
import re
import yfinance as yf
import google.generativeai as genai
from openai import OpenAI

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Takip edilecek popüler BIST 30/50 hisseleri
BIST_HISSELERI = [
    "THYAO.IS", "BIMAS.IS", "AKBNK.IS", "ISCTR.IS", "TUPRS.IS", 
    "SAHOL.IS", "KCHOL.IS", "EREGL.IS", "FROTO.IS", "ASELS.IS",
    "SISE.IS", "PGSUS.IS", "GARAN.IS", "YKBNK.IS", "ENKAI.IS"
]

def canli_fiyatlari_al():
    """BIST hisselerinin güncel son kapanış/canlı fiyatlarını çeker."""
    fiyatlar = {}
    try:
        data = yf.download(BIST_HISSELERI, period="1d", progress=False)['Close']
        for hisse in BIST_HISSELERI:
            kisa_kod = hisse.replace(".IS", "")
            if not data.empty and hisse in data.columns:
                fiyat = round(float(data[hisse].iloc[-1]), 2)
                fiyatlar[kisa_kod] = fiyat
    except Exception as e:
        print(f"Fiyat çekme hatası: {e}")
    return fiyatlar

def prompt_olustur(canli_fiyat_dict):
    fiyat_metni = "\n".join([f"- {kod}: {fiyat} TL" for kod, fiyat in canli_fiyat_dict.items()])
    
    return f"""
Sen uzman bir BIST (Borsa İstanbul) hisse senedi analistisin.
Aşağıda sana BIST hisselerinin GERÇEK VE CANLI GÜNCEL FİYATLARI verilmiştir:

CANLI FİYAT LİSTESİ:
{fiyat_metni}

GÖREVİN:
1. Yukarıda verilen CANLI FİYAT LİSTESİ'ndeki güncel fiyatları ESAS ALARAK en yüksek potansiyele sahip EN İYİ 15 hisseyi seç.
2. Verilen "fiyat" değerini KESİNLİKLE değiştirmeden JSON'a yaz.
3. Hedef fiyat ve potansiyeli bu canlı fiyata göre hesapla.

YAPIŞTIRILACAK YANIT SADECE AŞAĞIDAKİ JSON FORMATINDA OLMALIDIR:
[
  {{
    "hisse": "THYAO",
    "fiyat": 305.50,
    "hedef": 420.00,
    "potansiyel": "%37.5",
    "puan": 92,
    "ozet": "Güçlü yolcu trafiği ve kârlılık beklentisi."
  }}
]
"""

def json_temizle_ve_yukle(metin):
    try:
        match = re.search(r'\[.*\]', metin, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        return json.loads(metin)
    except Exception as e:
        print(f"JSON Ayrıştırma Hatası: {e}")
        return []

def gpt_analiz_yap(prompt):
    if not OPENAI_API_KEY:
        return []
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Sadece geçerli bir JSON dizisi yanıtı ver."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5
        )
        return json_temizle_ve_yukle(response.choices[0].message.content)
    except Exception as e:
        print(f"ChatGPT API Hatası: {e}")
        return []

def gemini_analiz_yap(prompt):
    if not GEMINI_API_KEY:
        return []
    
    modeller = ['gemini-3.6-flash', 'gemini-1.5-flash-8b', 'gemini-2.0-flash-exp']
    for model_adi in modeller:
        try:
            model = genai.GenerativeModel(model_adi)
            response = model.generate_content(prompt)
            sonuc = json_temizle_ve_yukle(response.text)
            if sonuc:
                return sonuc
        except Exception:
            continue
    return []

def cift_ai_analiz_yap():
    print("Canlı Fiyatlar Çekiliyor...")
    canli_fiyatlar = canli_fiyatlari_al()
    prompt = prompt_olustur(canli_fiyatlar)

    print("Canlı AI Analiz Taraması Başlatıldı...")
    gpt_liste = gpt_analiz_yap(prompt)
    gemini_liste = gemini_analiz_yap(prompt)

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
                    gpt_puan, gemini_puan, ort_puan = 0, 0, "-"

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
