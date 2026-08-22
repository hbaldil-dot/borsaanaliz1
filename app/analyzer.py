import yfinance as yf
import pandas as pd
import numpy as np

def hisse_analiz_et(hisse_kodu: str):
    try:
        symbol = f"{hisse_kodu}.IS"
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="3m")
        
        if df.empty or len(df) < 5:
            return None
            
        fiyat = float(df['Close'].iloc[-1])
        d1 = float(df['High'].rolling(10, min_periods=1).max().iloc[-1])
        d2 = float(df['High'].rolling(20, min_periods=1).max().iloc[-1])
        
        # Basit Hareketli Ortalama & Puanlama
        sma20 = float(df['Close'].rolling(20, min_periods=1).mean().iloc[-1])
        puan = 85 if fiyat > sma20 else 65
        
        hedef_fiyat = fiyat * (1 + (puan / 150))
        potansiyel = ((hedef_fiyat - fiyat) / fiyat) * 100
        
        return {
            "hisse": hisse_kodu,
            "fiyat": f"{fiyat:.2f}",
            "hedef_fiyat": f"{hedef_fiyat:.2f}",
            "potansiyel": f"+%{potansiyel:.1f}",
            "direnc": f"{d1:.2f} / {d2:.2f}",
            "puan": puan
        }
    except Exception as e:
        print(f"Hata ({hisse_kodu}): {e}")
        return None
