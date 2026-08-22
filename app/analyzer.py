import os
import json
import requests
import google.generativeai as genai
import yfinance as yf

# API Anahtarları (Render Environment Variables üzerinden okunur)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

PROMPT_TEXT = """
Sen uzman bir BIST borsa analistisin. Aşağıdaki 3 aşamalı analizi tüm BIST pay piyasası üzerinde GERÇEK ZAMANLI uygula:

[AŞAMA 1: ELEME VE İLK 100]
1. 2026 Yılı Karlılığı: Net Dönem Karı > 0 olanlar.
2. Zirve/Fiyat Oranı: 12 Aylık En Yüksek Fiyat / Güncel Fiyat oranı en yüksek olanlar.
3. USD Bazlı Ucuzluk: Geçmiş 3-5 yıllık USD fiyat ortalamalarına ve zirvelerine göre belirgin iskonto içerenler.

[AŞAMA 2 & 3: DETAYLI ANALİZ VE İLK 20 SEÇİMİ]
Teknik grafik formasyonları (çanak-kulp, düşen kırılımı), KAP haber akışı ve F/K, PD/DD çarpanlarını analiz ederek önümüzdeki 6 ayda en yüksek potansiyele sahip İLK 20 HİSSEYİ seç. 100 üzerinden puanla.

[SADECE VE SADECE AŞAĞIDAKİ JSON FORMATINDA YANIT VER, BAŞKA METİN YAZMA]:
[
  {
    "hisse": "HİSSE_KODU",
    "puan": 85,
    "hedef": 120.0,
    "d": "D1/D2",
    "ozet": "Teknik ve KAP gerekçesi"
  }
]
"""

def call_chatgpt():
    if not OPENAI_API_KEY:
        return []
    try:
        headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": "gpt-4o",
            "messages": [{"role": "system", "content": "You output only clean JSON."}, {"role": "user", "content": PROMPT_TEXT}],
            "temperature": 0.2
        }
        res = requests.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers, timeout=40)
        content = res.json()['choices'][0]['message']['content'].strip()
        return json.loads(content.replace("```json", "").replace("```", ""))
    except Exception as e:
        print(f"ChatGPT API Hatası: {e}")
        return []

def call_gemini():
    if not GEMINI_API_KEY:
        return []
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        res = model.generate_content(PROMPT_TEXT)
        text = res.text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception as e:
        print(f"Gemini API Hatası: {e}")
        return []

def cift_ai_analiz_yap():
    # Kodun içinde hiçbir hisse adı YOKTUR. Tamamen AI sorguları canlı çalışır.
    chatgpt_raw = call_chatgpt()
    gemini_raw = call_gemini()

    # Yahoo Finance üzerinden canlı son fiyatları ve potansiyelleri tamamlama
    def verileri_zenginlestir(ai_list):
        for item in ai_list:
            try:
                df = yf.Ticker(f"{item['hisse']}.IS").history(period="2d")
                fiyat = float(df['Close'].iloc[-1]) if not df.empty else 100.0
            except:
                fiyat = 100.0
            item['fiyat'] = f"{fiyat:.2f}"
            pot = ((item['hedef'] - fiyat) / fiyat) * 100
            item['potansiyel'] = f"+%{pot:.1f}"
            item['hedef'] = f"{item['hedef']:.2f}"
        return ai_list

    chatgpt_listesi = verileri_zenginlestir(chatgpt_raw)
    gemini_listesi = verileri_zenginlestir(gemini_raw)

    # Ortak Kesişim Hesabı
    gpt_kodlar = {x["hisse"] for x in chatgpt_listesi}
    gemini_kodlar = {x["hisse"] for x in gemini_listesi}
    ortak_kodlar = gpt_kodlar.intersection(gemini_kodlar)

    ortak_listesi = []
    for item in chatgpt_listesi:
        if item["hisse"] in ortak_kodlar:
            g_item = next((g for g in gemini_listesi if g["hisse"] == item["hisse"]), item)
            ortak_listesi.append({
                "hisse": item["hisse"],
                "fiyat": item["fiyat"],
                "gpt_puan": item["puan"],
                "gemini_puan": g_item["puan"],
                "ort_puan": int((item["puan"] + g_item["puan"]) / 2),
                "potansiyel": item["potansiyel"],
                "ozet": f"<b>ChatGPT:</b> {item['ozet']}<br><b>Gemini:</b> {g_item['ozet']}"
            })

    ortak_listesi.sort(key=lambda x: x["ort_puan"], reverse=True)

    return {
        "gpt": chatgpt_listesi,
        "gemini": gemini_listesi,
        "ortak": ortak_listesi
    }
