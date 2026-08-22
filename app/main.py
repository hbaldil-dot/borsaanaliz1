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
        return '<tr><td colspan="7" style="text-align:center; padding:15px; color:#64748b;">Henüz canlı tarama yapılmadı. Taramayı başlatmak için yukarıdaki butona tıklayın.</td></tr>'
    
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
        ortak_html = '<tr><td colspan="7" style="text-align:center; padding:15px; color:#64748b;">Henüz canlı tarama yapılmadı. Ortak kesişim listesi için "🔄 Taramayı Yenile" butonuna basın.</td></tr>'
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
        <title>BIST AI Üçlü Analiz Paneli</title>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, sans-serif; background-color: #f1f5f9; margin: 20px; }}
            .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }}
            .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #e2e8f0; padding-bottom: 15px; margin-bottom: 25px; }}
            .btn {{ background-color: #16a34a; color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 15px; }}
            .btn:hover {{ background-color: #15803d; }}
            table {{ width: 100%; border-collapse: collapse; font-size: 14px; margin-top: 10px; }}
            th, td {{ padding: 10px 12px; border-bottom: 1px solid #e2e8f0; text-align: left; }}
            th {{ background-color: #f8fafc; font-weight: 600; color: #334155; }}
            .badge {{ background-color: #2563eb; color: white; padding: 3px 10px; border-radius: 12px; font-weight: bold; font-size: 12px; }}
            .badge-gold {{ background-color: #d97706; color: white; padding: 4px 12px; border-radius: 12px; font-weight: bold; font-size: 14px; }}
            .card {{ border: 1px solid #e2e8f0; border-radius: 10px; padding: 20px; background: #fff; margin-bottom: 30px; }}
            .title-gemini {{ color: #7c3aed; font-size: 20px; margin-top:0; border-bottom: 2px solid #7c3aed; padding-bottom: 8px; }}
            .title-gpt {{ color: #2563eb; font-size: 20px; margin-top:0; border-bottom: 2px solid #2563eb; padding-bottom: 8px; }}
            .title-ortak {{ color: #15803d; font-size: 20px; margin-top:0; border-bottom: 2px solid #15803d; padding-bottom: 8px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div>
                    <h1 style="margin:0; color:#0f172a;">🤖 BIST AI Canlı Analiz Konsensüsü</h1>
                    <p style="margin:5px 0 0 0; color:#64748b;">Gemini, ChatGPT ve Ortak Kesişim Tablosu</p>
                </div>
                <a href="/run-scan" class="btn">🔄 Taramayı Yenile</a>
            </div>

            <!-- 1. BÖLÜM: GEMINI 20 HİSSE -->
            <div class="card" style="border-left: 5px solid #7c3aed;">
                <h2 class="title-gemini">🟣 1. GEMINI ANALİZİ (EN İYİ 20 HİSSE)</h2>
                <table>
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>Hisse</th>
                            <th>Fiyat</th>
                            <th>Hedef</th>
                            <th>Potansiyel Getiri</th>
                            <th>Puan</th>
                            <th>Gemini Analiz Notu</th>
                        </tr>
                    </thead>
                    <tbody>
                        {tablo_olustur(VERILER["gemini"])}
                    </tbody>
                </table>
            </div>

            <!-- 2. BÖLÜM: CHATGPT 20 HİSSE -->
            <div class="card" style="border-left: 5px solid #2563eb;">
                <h2 class="title-gpt">🔵 2. CHATGPT ANALİZİ (EN İYİ 20 HİSSE)</h2>
                <table>
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>Hisse</th>
                            <th>Fiyat</th>
                            <th>Hedef</th>
                            <th>Potansiyel Getiri</th>
                            <th>Puan</th>
                            <th>ChatGPT Analiz Notu</th>
                        </tr>
                    </thead>
                    <tbody>
                        {tablo_olustur(VERILER["gpt"])}
                    </tbody>
                </table>
            </div>

            <!-- 3. BÖLÜM: ORTAK KESİŞİM HİSRELERİ -->
            <div class="card" style="border: 2px solid #22c55e; background-color: #fafdfb;">
                <h2 class="title-ortak">🎯 3. ORTAK KESİŞİM HİSRELERİ (İki AI Modelinin de Seçtikleri)</h2>
                <table>
                    <thead>
                        <tr style="background-color: #dcfce7;">
                            <th>#</th>
                            <th>Hisse</th>
                            <th>Fiyat</th>
                            <th>Puanlar (GPT / Gemini)</th>
                            <th>Ort. Puan</th>
                            <th>Potansiyel</th>
                            <th>AI Ortak Değerlendirmesi</th>
                        </tr>
                    </thead>
                    <tbody>
                        {ortak_html}
                    </tbody>
                </table>
            </div>

        </div>
    </body>
    </html>
    """
