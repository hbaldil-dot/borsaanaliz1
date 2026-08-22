from fastapi import FastAPI
from fastapi.responses import HTMLResponse, RedirectResponse
from contextlib import asynccontextmanager
from app.scheduler import scheduler_baslat
from app.analyzer import cift_ai_analiz_yap

VERILER = {"gpt": [], "gemini": [], "ortak": []}

@asynccontextmanager
async def lifespan(app: FastAPI):
    global VERILER
    scheduler_baslat()
    # Uygulama açılırken canlı API'lerden veriyi çeker
    VERILER = cift_ai_analiz_yap()
    yield

app = FastAPI(title="BIST Çift AI Analiz Motoru", lifespan=lifespan)

@app.get("/run-scan")
def manuel_tarama():
    global VERILER
    VERILER = cift_ai_analiz_yap()
    return RedirectResponse(url="/", status_code=303)

def tablo_olustur(liste):
    html = ""
    if not liste:
        return '<tr><td colspan="7" style="text-align:center; padding:15px; color:#64748b;">Henüz analiz verisi yok veya API yanıt bekleniyor...</td></tr>'
    
    for idx, item in enumerate(liste, start=1):
        html += f"""
        <tr>
            <td style="text-align: center; font-weight: bold;">{idx}</td>
            <td style="font-weight: bold; color: #1e3a8a;">{item.get('hisse', '-')}</td>
            <td>{item.get('fiyat', '-')} TL</td>
            <td>{item.get('hedef', '-')} TL</td>
            <td style="color: #16a34a; font-weight: bold;">{item.get('potansiyel', '-')}</td>
            <td><span class="badge">{item.get('puan', '-')}</span></td>
            <td style="font-size: 12px; color: #475569;">{item.get('ozet', '-')}</td>
        </tr>
        """
    return html

@app.get("/", response_class=HTMLResponse)
def web_arayuzu():
    ortak_html = ""
    if not VERILER["ortak"]:
        ortak_html = '<tr><td colspan="7" style="text-align:center; padding:15px; color:#64748b;">Ortak kesişim hisselerini görmek için "🔄 Taramayı Yenile" butonuna basın.</td></tr>'
    else:
        for idx, item in enumerate(VERILER["ortak"], start=1):
            ortak_html += f"""
            <tr style="background-color: #f0fdf4;">
                <td style="text-align: center; font-weight: bold;">{idx}</td>
                <td style="font-weight: bold; color: #15803d; font-size:16px;">{item.get('hisse', '-')}</td>
                <td><b>{item.get('fiyat', '-')} TL</b></td>
                <td>{item.get('gpt_puan', '-')} / {item.get('gemini_puan', '-')}</td>
                <td style="text-align: center;"><span class="badge-gold">{item.get('ort_puan', '-')}</span></td>
                <td style="color: #16a34a; font-weight: bold;">{item.get('potansiyel', '-')}</td>
                <td style="font-size: 12px;">{item.get('ozet', '-')}</td>
            </tr>
            """

    return f"""
    <!DOCTYPE html>
    <html lang="tr">
    <head>
        <meta charset="UTF-8">
        <title>BIST Çift AI Analiz Konsensüsü</title>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, sans-serif; background-color: #f1f5f9; margin: 15px; }}
            .container {{ max-width: 1400px; margin: 0 auto; background: white; padding: 20px; border-radius: 12px; }}
            .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #e2e8f0; padding-bottom: 15px; margin-bottom: 20px; }}
            .btn {{ background-color: #16a34a; color: white; padding: 10px 20px; text-decoration: none; border-radius: 8px; font-weight: bold; }}
            .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 20px; }}
            table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
            th, td {{ padding: 8px 10px; border-bottom: 1px solid #e2e8f0; text-align: left; }}
            th {{ background-color: #f8fafc; }}
            .badge {{ background-color: #2563eb; color: white; padding: 2px 8px; border-radius: 12px; font-weight: bold; }}
            .badge-gold {{ background-color: #d97706; color: white; padding: 4px 10px; border-radius: 12px; font-weight: bold; font-size: 14px; }}
            .card {{ border: 1px solid #cbd5e1; border-radius: 8px; padding: 15px; background: #fff; }}
            .title-ortak {{ color: #15803d; font-size: 18px; margin-top:0; }}
            .title-gpt {{ color: #2563eb; font-size: 16px; margin-top:0; }}
            .title-gemini {{ color: #7c3aed; font-size: 16px; margin-top:0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div>
                    <h1 style="margin:0;">🤖 ChatGPT & Gemini BIST Analiz Konsensüsü</h1>
                    <p style="margin:5px 0 0 0; color:#64748b;">3 Aşamalı Canlı AI Sorgusuyla Oluşturulan Kesişim Listesi</p>
                </div>
                <a href="/run-scan" class="btn">🔄 Taramayı Yenile</a>
            </div>

            <!-- 3. TABLO: KONSENSÜS / ORTAK HİSSELER -->
            <div class="card" style="border: 2px solid #22c55e; background-color: #fafdfb; margin-bottom: 25px;">
                <h2 class="title-ortak">🎯 1. ÇİFT AI KONSENSÜS TABLOSU (Her İki Modelin Ortak Seçimleri)</h2>
                <table>
                    <thead>
                        <tr style="background-color: #dcfce7;">
                            <th>#</th>
                            <th>Hisse</th>
                            <th>Fiyat</th>
                            <th>Puanlar (GPT / Gemini)</th>
                            <th>Ort. Puan</th>
                            <th>Potansiyel</th>
                            <th>AI Ortak Analiz Notu</th>
                        </tr>
                    </thead>
                    <tbody>
                        {ortak_html}
                    </tbody>
                </table>
            </div>

            <!-- EKRANI 2'YE BÖLEN TABLOLAR -->
            <div class="grid-2">
                <!-- CHATGPT TABLOSU -->
                <div class="card">
                    <h3 class="title-gpt">🔵 ChatGPT En İyi 20 Hisse</h3>
                    <table>
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>Hisse</th>
                                <th>Fiyat</th>
                                <th>Hedef</th>
                                <th>Getiri</th>
                                <th>Puan</th>
                                <th>Özet</th>
                            </tr>
                        </thead>
                        <tbody>
                            {tablo_olustur(VERILER["gpt"])}
                        </tbody>
                    </table>
                </div>

                <!-- GEMINI TABLOSU -->
                <div class="card">
                    <h3 class="title-gemini">🟣 Gemini En İyi 20 Hisse</h3>
                    <table>
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>Hisse</th>
                                <th>Fiyat</th>
                                <th>Hedef</th>
                                <th>Getiri</th>
                                <th>Puan</th>
                                <th>Özet</th>
                            </tr>
                        </thead>
                        <tbody>
                            {tablo_olustur(VERILER["gemini"])}
                        </tbody>
                    </table>
                </div>
            </div>

        </div>
    </body>
    </html>
    """
