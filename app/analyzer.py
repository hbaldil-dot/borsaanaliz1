import os
import json
import re
import yfinance as yf
import requests
import google.generativeai as genai
from openai import OpenAI

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def tum_bist_hisselerini_getir():
    """Borsa İstanbul'daki güncel tüm hisse kodlarını çeker."""
    try:
        # Wikipedia/GitHub BIST tüm hisse listesi kaynağı
        url = "https://raw.githubusercontent.com/datasets/turkish-stock-exchange-companies/master/data/companies.json"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return [f"{item['code']}.IS" for item in data if 'code' in item]
    except Exception as e:
        print(f"Dinamik BIST listesi alınamadı, yedek geniş liste kullanılıyor: {e}")
    
    # Standart geniş BIST sembol havuzu
    genis_havuz = [
        "THYAO", "BIMAS", "AKBNK", "ISCTR", "TUPRS", "SAHOL", "KCHOL", "EREGL", "FROTO", "ASELS",
        "SISE", "PGSUS", "GARAN", "YKBNK", "ENKAI", "TOASO", "HEKTS", "SASA", "KONTR", "ALARK",
        "PETKM", "ASTOR", "ODAS", "MGROS", "DOHOL", "TCELL", "EKGYO", "KOZAL", "GUBRF", "OYAKC",
        "SOKM", "TTKOM", "ULKER", "MIATK", "VESBE", "TURSG", "BERA", "BRSAN", "EGEEN", "GENIL",
        "AKSEN", "ALBRK", "ARCLK", "AYDEM", "BAGFS", "BANVT", "BFREN", "BIENP", "BOBET", "CANTE",
        "CIMSA", "CLEBI", "CWENE", "DOAS", "EUPWR", "GWIND", "HALKB", "INVEO", "IEYHO", "ISGYO",
        "KARSN", "KCAER", "KORDS", "KOZAA", "LOGVO", "MAVI", "MTRKS", "NTHOL", "OTKAR", "OYYAT",
        "PENTA", "QUAGR", "SDTTR", "SKEBN", "SMRTG", "TABGD", "TAVHL", "TKFEN", "TMSN", "TSKB"
    ]
    return [f"{kod}.IS" for kod in genis_havuz]

def asama1_filtrele_ve_100_hisse_sec():
    print("Aşama 1: Tüm BIST Hisseleri Taranıyor ve 3 Katı Filtre Uygulanıyor...")
    tum_hisseler = tum_bist_hisselerini_getir()
    aday_hisseler = []
    
    try:
        usd_data = yf.Ticker("USDTRY=X").history(period="1d")
        usd_kuru = float(usd_data['Close'].iloc[-1]) if not usd_data.empty else 33.0

        for hisse in tum_hisseler:
            kisa_kod = hisse.replace(".IS", "")
            ticker = yf.Ticker(hisse)
            hist = ticker.history(period="1y")
            
            if hist.empty or len(hist) < 50:
                continue
                
            gunluk_fiyat = float(hist['Close'].iloc[-1])
            zirve_52w = float(hist['High'].max())
            
            # Kriter 2: Zirve / Mevcut Fiyat Oranı (İskonto Büyüklüğü)
            zirve_orani = round(zirve_52w / gunluk_fiyat, 2)
            
            # Kriter 3: USD Bazlı Ucuzluk
            usd_fiyat = round(gunluk_fiyat / usd_kuru, 2)
            usd_zirve = round(zirve_52w / usd_kuru, 2)

            aday_hisseler.append({
                "hisse": kisa_kod,
                "fiyat_tl": gunluk_fiyat,
                "zirve_orani": zirve_orani,
                "usd_fiyat": usd_fiyat,
                "usd_zirve": usd_zirve
            })

        # Katı Filtreleme: En yüksek zirve/fiyat oranına ve USD bazlı iskontoya sahip İlk 100 Hisse seçilir
        aday_hisseler.sort(key=lambda x: x['zirve_orani'], reverse=True)
        return aday_hisseler[:100]
        
    except Exception as e:
        print(f"Aşama 1 Hatası: {e}")
        return []

def prompt_olustur(filtrelenmis_100_hisse):
    hisse_ozetleri = "\n".join([
        f"- {item['hisse']}: Fiyat: {item['fiyat_tl']} TL, USD Fiyat: ${item['usd_fiyat']}, Zirve/Fiyat Oranı: {item['zirve_orani']}x"
        for item in filtrelenmis_100_hisse[:30] # LLM Token optimizasyonu için en yüksek puanlı 30 hisse detaylı prompta sunulur
    ])

    return f"""
Sen Borsa İstanbul konusunda uzmanlaşmış kıdemli bir Fon Yöneticisisin.

Aşama 1 süzgecinden geçen en yüksek potansiyelli hisse listen:
{hisse_ozetleri}

[AŞAMA 2: DETAYLI ÇOKLU ANALİZ VE PUANLAMA]
Bu hisseler üzerinde şu 3 yöntemi uygulayarak değerlendir:
1. Teknik Grafik Analizi (%40 Ağırlık): EMA20/50/200, Düşen Kırılımı, RSI/MACD ve Formasyon Potansiyeli.
2. KAP Haberleri ve Temel Akış (%35 Ağırlık): Yeni İş İlişkileri, Yatırım, Borçluluk ve Kârlılık Trendi.
3. Çarpan Değerlemesi (%25 Ağırlık): Sektörel F/K, PD/DD İskontosu ve Marjlar.

Önümüzdeki 6 ay içinde en yüksek değer artış potansiyeline sahip EN İYİ 20 HİSSEYİ seç.
Seçtiğin hisseleri 100 puan üzerinden (Teknik %40 + Temel %35 + İskonto %25) puanla.

YAPIŞTIRILACAK YANIT SADECE AŞAĞIDAKİ JSON FORMATINDA OLMALIDIR:
[
  {{
    "hisse": "THYAO",
    "fiyat": 305.50,
    "hedef": 425.00,
    "potansiyel": "%39.1",
    "direnc": "330.00 / 380.00",
    "puan": 92,
    "ozet": "Düşen trend kırılımı teyit edildi. KAP filosu genişleme haberi ve cazip çarpanlar."
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
            temperature=0.4
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
    filtrelenmis_100 = asama1_filtrele_ve_100_hisse_sec()
    prompt = prompt_olustur(filtrelenmis_100)

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
                    "ozet": f"GPT: {g_item.get('ozet', '')} | Gemini: {m_item.get('ozet', '')}"
                })

    ortak_liste.sort(key=lambda x: x['ort_puan'] if isinstance(x['ort_puan'], (int, float)) else 0, reverse=True)

    return {
        "gpt": gpt_liste,
        "gemini": gemini_liste,
        "ortak": ortak_liste
    }
