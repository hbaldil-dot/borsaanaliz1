import yfinance as yf
import pandas as pd
import numpy as np

def hisse_analiz_et(hisse_kodu: str):
    symbol = f"{hisse_kodu}.IS"
    ticker = yf.Ticker(symbol)
    df = ticker.history(period="1y")

    if df.empty:
        return None

    fiyat = df['Close'].iloc[-1]
    d1 = df['High'].rolling(20).max().iloc[-1]
    d2 = df['High'].rolling(50).max().iloc[-1]

    rsi = calculate_rsi(df['Close'])
    puan = int(np.clip(100 - rsi, 40, 95))
    hedef_fiyat = fiyat * (1 + (puan / 200))
    potansiyel = ((hedef_fiyat - fiyat) / fiyat) * 100

    return {
        "hisse": hisse_kodu,
        "fiyat": round(fiyat, 2),
        "hedef_fiyat": round(hedef_fiyat, 2),
        "potansiyel": f"+%{round(potansiyel, 1)}",
        "direnc": f"{round(d1, 2)} / {round(d2, 2)}",
        "puan": puan
    }

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs.iloc[-1]))
