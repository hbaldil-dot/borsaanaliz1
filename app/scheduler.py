# app/scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler
from app.analyzer import hisse_analiz_et

# Takip edilecek hisse listesi
HISSELER = ["SAHOL", "PGSUS", "VESBE", "EKGYO", "ULKER", "FROTO", "DOAS", "ALARK", "KCHOL", "TURSG"]

def gunluk_tarama_yap():
    print("🚀 Otomatik BIST Taraması Başladı...")
    sonuclar = []
    
    for kod in HISSELER:
        veri = hisse_analiz_et(kod)
        if veri:
            sonuclar.append(veri)
            
    # Puanı yüksek olandan düşüğe doğru sırala
    sonuclar.sort(key=lambda x: x['puan'], reverse=True)
    
    print(f"✅ Tarama Tamamlandı! {len(sonuclar)} hisse analiz edildi.")
    return sonuclar

def scheduler_baslat():
    scheduler = BackgroundScheduler(timezone="Europe/Istanbul")
    
    # Hafta içi (Pazartesi-Cuma) 10:30, 14:30 ve 18:15'te otomatik çalışır
    scheduler.add_job(
        gunluk_tarama_yap, 
        'cron', 
        day_of_week='mon-fri', 
        hour='10,14,18', 
        minute='30'
    )
    scheduler.start()
    print("⏰ Otomatik zamanlayıcı (Cron) kuruldu ve başlatıldı.")
