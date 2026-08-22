from fastapi import FastAPI
from fastapi.responses import HTMLResponse, RedirectResponse
from contextlib import asynccontextmanager
from app.scheduler import scheduler_baslat
from app.analyzer import tam_ai_analiz_yap

SON_TARAMA_SONUCLARI = []

@asynccontextmanager
async def lifespan(app: FastAPI):
    global SON_TARAMA_SONUCLARI
    scheduler_baslat()
    yield

app = FastAPI(title="BIST AI Analiz Motoru", lifespan=lifespan)

@app.get("/run-scan")
def manuel_tarama():
    global SON_TARAMA_SONUCLARI
    res = tam_ai_analiz_yap()
    if res:
        SON_TARAMA_SONUCLARI = res
    return RedirectResponse(url="/", status_code=303)

@app.get("/", response_class=HTMLResponse)
def web_arayuzu():
    satirlar_html = ""
    if not SON_TARAMA_SONUCLARI:
        satirlar_html = '<tr><td colspan="8" style="text-align:center; padding: 20px; color: #64748b;">3 Aşamalı AI Analizi çalıştırmak için "🔄 Şimdi Taramayı Başlat" butonuna basın.</td></tr>'
    else:
        for idx, item in enumerate(SON_TARAMA_SONUCLARI, start=1):
            satirlar_html += f"""
            <tr>
                <td style="text-align: center; font-weight: bold;">{idx}</td>
                <td style="font-weight: bold; color: #1e3a8a;">{item['hisse']}</td>
                <td>{item['fiyat']} TL</td>
                <td>{item['hedef_fiyat']} TL</td>
                <td style="color: #16a34a; font-weight: bold;">{item['potansiyel']}</td>
                <td>{item['direnc']}</td>
                <td style="text-align: center;"><span class="badge">{item['puan']}</span></td>
                <td style="font-size: 13px; color: #475569;">{item.get('ozet', '-')}</td>
            </tr>
            """

    return f"""
    <!DOCTYPE html>
    <html lang="tr">
    <head>
        <meta charset="UTF-8">
        <title>BIST AI Hisse Analiz Tablosu</title>
        <style>
            body {{ font-family: sans-serif; background-color: #f8fafc; margin: 20px; }}
            .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }}
            .header-flex {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }}
            .btn {{ background-color: #16a34a; color: white; padding: 10px 18px; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 14px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
            th, td {{ padding: 12px 15px; text-align: left; border-bottom: 1px solid #e2e8f0; }}
            th {{ background-color: #f1f5f9; }}
            .badge {{ background-color: #2563eb; color: white; padding: 4px 10px; border-radius: 20px; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header-flex">
                <div>
                    <h1 style="margin:0;">📊 BIST 3 Aşamalı AI Analiz Tablosu</h1>
                    <p style="margin:5px 0 0 0; color:#64748b;">Karlılık, USD İskonto, KAP ve Teknik Grafik Analizli Canlı Liste</p>
                </div>
                <a href="/run-scan" class="btn">🔄 Şimdi Taramayı Başlat</a>
            </div>
            <table>
                <thead>
                    <tr>
                        <th style="text-align: center;">Sıra</th>
                        <th>Hisse Kodu</th>
                        <th>Bugünkü Fiyat</th>
                        <th>6 Ay Öngörü</th>
                        <th>Potansiyel Getiri</th>
                        <th>Dirençler (D1/D2)</th>
                        <th style="text-align: center;">Puan</th>
                        <th>Kısa Analiz Özeti</th>
                    </tr>
                </thead>
                <tbody>
                    {satirlar_html}
                </tbody>
            </table>
        </div>
    </body>
    </html>
    """
