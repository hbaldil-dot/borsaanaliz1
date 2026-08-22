from apscheduler.schedulers.background import BackgroundScheduler
from app.analyzer import cift_ai_analiz_yap

scheduler = BackgroundScheduler()

def zamanlanmis_gorev():
    print("Zamanlanmış otomatik BIST AI taraması çalıştırılıyor...")
    cift_ai_analiz_yap()

def scheduler_baslat():
    # Günde 3 kez (borsa açılış, öğle, kapanış) otomatik tarama
    scheduler.add_job(zamanlanmis_gorev, 'cron', hour='09,13,18', minute='30')
    scheduler.start()
