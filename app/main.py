# app/main.py
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager
from app.scheduler import scheduler_baslat, gunluk_tarama_yap

# En son yapılan tarama sonuçlarını hafızada tutmak için
SON_TARAMA_SONUCLARI = []

@asynccontextmanager
async def lifespan(app: FastAPI):
    global SON_TARAMA_SONUCLARI
    # Uygulama başladığında zamanlayıcıyı devreye sok
    scheduler_baslat()
    # İlk açılışta hemen bir tarama yap
    SON_TARAMA_SONUCLARI = gunluk_tarama_yap()
    yield

app = FastAPI(title="BIST AI Analiz Motoru", lifespan=lifespan)

@app.get("/api/scan")
def api_scan():
    """Mobil/Frontend uygulamaları için JSON API çıktısı"""
    return {"status": "success", "data": SON_TARAMA_SONUCLARI}

@app.get("/", response_class=HTMLResponse)
def web_arayuzu():
    """PDF formatındaki canlı web tablosu"""
    
    satirlar_html = ""
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
        </tr>
        """

    html_content = f"""
    <!DOCTYPE html>
    <html lang="tr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>BIST AI Hisse Analiz Tablosu</title>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8fafc; margin: 20px; padding: 0; }}
            .container {{ max-width: 1100px; margin: 0 auto; background: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }}
            h1 {{ color: #0f172a; margin-bottom: 5px; }}
            p.sub {{ color: #64748b; font-size: 14px; margin-bottom: 20px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
            th, td {{ padding: 12px 15px; text-align: left; border-bottom: 1px solid #e2e8f0; }}
            th {{ background-color: #f1f5f9; color: #334155; font-weight: 600; font-size: 14px; }}
            tr:hover {{ background-color: #f8fafc; }}
            .badge {{ background-color: #2563eb; color: white; padding: 4px 10px; border-radius: 20px; font-weight: bold; font-size: 13px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📊 BIST Günlük Analiz Tablosu</h1>
            <p class="sub">Günde 3 defa otomatik güncellenen teknik ve potansiyel değerlendirme tablosu.</p>
            <table>
                <thead>
                    <tr>
                        <th style="text-align: center;">Sıra</th>
                        <th>Hisse Kodu</th>
                        <th>Bugünkü Fiyat</th>
                        <th>6 Ay Sonra Öngörü</th>
                        <th>Potansiyel Getiri</th>
                        <th>Direnç Seviyeleri (D1/D2)</th>
                        <th style="text-align: center;">Puan (100)</th>
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
    return html_content
