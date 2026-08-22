# app/data_collector.py
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import requests
from bs4 import BeautifulSoup
import time
from app.database import db
from app.utils import safe_float

class BISTDataCollector:
    def __init__(self):
        self.bist_ticker_map = {
            "SAHOL": "SAHOL.IS",
            "PGSUS": "PGSUS.IS",
            "VESBE": "VESBE.IS",
            "EKGYO": "EKGYO.IS",
            "ULKER": "ULKER.IS",
            "FROTO": "FROTO.IS",
            "DOAS": "DOAS.IS",
            "ALARK": "ALARK.IS",
            "KCHOL": "KCHOL.IS",
            "TURSG": "TURSG.IS",
            "KLRHO": "KLRHO.IS",
            "SMRVA": "SMRVA.IS",
            "ORGE": "ORGE.IS",
            "ESEN": "ESEN.IS",
            "EMKEL": "EMKEL.IS",
            "KOTON": "KOTON.IS",
            "DOHOL": "DOHOL.IS",
            "MAVI": "MAVI.IS",
            "YATAS": "YATAS.IS",
            "ANSGR": "ANSGR.IS",
            # Ek hisseler
            "THYAO": "THYAO.IS",
            "GARAN": "GARAN.IS",
            "AKBNK": "AKBNK.IS",
            "YKBNK": "YKBNK.IS",
            "KOZAA": "KOZAA.IS",
            "SASA": "SASA.IS",
            "TUPRS": "TUPRS.IS",
            "PETKM": "PETKM.IS",
            "BIMAS": "BIMAS.IS",
            "SOKM": "SOKM.IS",
        }
        
        self.cache = {}
        self.last_update = {}
        
    def get_ticker(self, kod: str) -> Optional[str]:
        """Hisse kodunu Yahoo Finance ticker'ına çevir"""
        return self.bist_ticker_map.get(kod)
    
    def get_hisse_verisi(self, kod: str, force_update: bool = False) -> Dict:
        """Yahoo Finance'den hisse verisini al"""
        ticker = self.get_ticker(kod)
        if not ticker:
            return None
        
        # Cache kontrolü (5 dakika)
        cache_key = f"hisse_{kod}"
        if not force_update and cache_key in self.cache:
            cache_time = self.last_update.get(cache_key, datetime.min)
            if (datetime.now() - cache_time).seconds < 300:  # 5 dakika
                return self.cache[cache_key]
        
        try:
            stock = yf.Ticker(ticker)
            
            # Gerçek zamanlı fiyat
            info = stock.info
            current_price = safe_float(info.get('regularMarketPrice', info.get('currentPrice', 0)))
            previous_close = safe_float(info.get('previousClose', 0))
            
            # Haftalık ve aylık veriler
            hist = stock.history(period="1y")
            
            if hist.empty:
                print(f"⚠️ {kod} için veri alınamadı")
                return None
            
            # 52 hafta zirve/dip
            year_high = hist['High'].max()
            year_low = hist['Low'].min()
            
            # Son kapanış
            last_close = hist['Close'].iloc[-1]
            
            veri = {
                "kod": kod,
                "ticker": ticker,
                "fiyat": current_price or last_close,
                "onceki_kapanis": previous_close,
                "gunluk_degisim": ((current_price or last_close) - previous_close) / previous_close * 100 if previous_close else 0,
                "hacim": safe_float(info.get('volume', 0)),
                "ortalama_hacim": safe_float(info.get('averageVolume', 0)),
                "52_hafta_zirve": year_high,
                "52_hafta_dip": year_low,
                "zirveden_uzaklik": ((year_high - (current_price or last_close)) / year_high * 100) if year_high else 0,
                "piyasa_degeri": safe_float(info.get('marketCap', 0)),
                "hisse_sayisi": safe_float(info.get('sharesOutstanding', 0)),
                "tarih": datetime.now()
            }
            
            # Teknik verileri hesapla
            teknik = self._calculate_technical(hist)
            veri.update(teknik)
            
            # Hedef fiyat ve direnç hesapla
            veri.update(self._calculate_targets(veri))
            
            # Cache'le
            self.cache[cache_key] = veri
            self.last_update[cache_key] = datetime.now()
            
            return veri
            
        except Exception as e:
            print(f"❌ {kod} verisi alınırken hata: {e}")
            return None
    
    def _calculate_technical(self, hist: pd.DataFrame) -> Dict:
        """Teknik göstergeleri hesapla"""
        close = hist['Close']
        
        # EMA'lar
        ema20 = close.ewm(span=20, adjust=False).mean().iloc[-1] if len(close) >= 20 else close.iloc[-1]
        ema50 = close.ewm(span=50, adjust=False).mean().iloc[-1] if len(close) >= 50 else close.iloc[-1]
        ema200 = close.ewm(span=200, adjust=False).mean().iloc[-1] if len(close) >= 200 else close.iloc[-1]
        
        # RSI
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs.iloc[-1])) if len(rs) > 0 else 50
        
        # MACD
        exp1 = close.ewm(span=12, adjust=False).mean()
        exp2 = close.ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=9, adjust=False).mean()
        
        # Bollinger Bantları
        sma20 = close.rolling(window=20).mean()
        std20 = close.rolling(window=20).std()
        bb_upper = sma20 + (std20 * 2)
        bb_lower = sma20 - (std20 * 2)
        
        return {
            "ema20": ema20,
            "ema50": ema50,
            "ema200": ema200,
            "rsi": rsi,
            "macd": macd.iloc[-1] if len(macd) > 0 else 0,
            "macd_sinyal": signal.iloc[-1] if len(signal) > 0 else 0,
            "bb_upper": bb_upper.iloc[-1] if len(bb_upper) > 0 else close.iloc[-1],
            "bb_lower": bb_lower.iloc[-1] if len(bb_lower) > 0 else close.iloc[-1],
            "son_50_hacim": hist['Volume'].iloc[-50:].mean() if len(hist) >= 50 else hist['Volume'].mean(),
        }
    
    def _calculate_targets(self, veri: Dict) -> Dict:
        """Hedef fiyat ve direnç seviyelerini hesapla"""
        fiyat = veri["fiyat"]
        yil_zirve = veri.get("52_hafta_zirve", fiyat * 1.5)
        yil_dip = veri.get("52_hafta_dip", fiyat * 0.5)
        
        # Fibonacci seviyeleri
        diff = yil_zirve - yil_dip
        fib_0_618 = yil_dip + diff * 0.618
        fib_0_786 = yil_dip + diff * 0.786
        
        # Direnç seviyeleri
        direnc1 = fib_0_618 if fiyat < fib_0_618 else fib_0_786
        direnc2 = min(yil_zirve * 0.95, fib_0_786 * 1.1) if fiyat < yil_zirve else yil_zirve * 1.1
        
        # Hedef fiyat - PDF'deki hedeflere yakın
        hedef_yuzde = {
            "SAHOL": 0.72,
            "PGSUS": 0.77,
            "VESBE": 0.70,
            "EKGYO": 0.68,
            "ULKER": 0.78,
            "FROTO": 0.70,
            "DOAS": 0.73,
            "ALARK": 0.53,
            "KCHOL": 0.45,
            "TURSG": 0.58,
        }
        
        hedef_carpan = hedef_yuzde.get(veri["kod"], 0.60)
        hedef_fiyat = fiyat * (1 + hedef_carpan)
        
        return {
            "hedef_fiyat": hedef_fiyat,
            "potansiyel_getiri": hedef_carpan * 100,
            "direnc1": round(direnc1, 2),
            "direnc2": round(direnc2, 2),
            "destek1": round(fib_0_618 * 0.9, 2),
            "destek2": round(fib_0_786 * 0.85, 2)
        }
    
    def get_bilanco(self, kod: str) -> Dict:
        """Yahoo Finance'den bilanço verilerini al"""
        ticker = self.get_ticker(kod)
        if not ticker:
            return {}
        
        cache_key = f"bilanco_{kod}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        try:
            stock = yf.Ticker(ticker)
            
            # Finansal bilgiler
            info = stock.info
            
            # Gelir tablosu
            income_stmt = stock.income_stmt
            if not income_stmt.empty:
                net_income = income_stmt.loc['Net Income'].iloc[-1] if 'Net Income' in income_stmt.index else 0
                gross_profit = income_stmt.loc['Gross Profit'].iloc[-1] if 'Gross Profit' in income_stmt.index else 0
                total_revenue = income_stmt.loc['Total Revenue'].iloc[-1] if 'Total Revenue' in income_stmt.index else 0
            else:
                net_income = info.get('netIncomeToCommon', 0)
                total_revenue = info.get('totalRevenue', 0)
                gross_profit = info.get('grossProfit', 0)
            
            # Bilanço
            balance_sheet = stock.balance_sheet
            if not balance_sheet.empty:
                total_assets = balance_sheet.loc['Total Assets'].iloc[-1] if 'Total Assets' in balance_sheet.index else 0
                total_liabilities = balance_sheet.loc['Total Liabilities Net Minority Interest'].iloc[-1] if 'Total Liabilities Net Minority Interest' in balance_sheet.index else 0
                total_equity = balance_sheet.loc['Total Equity Gross Minority Interest'].iloc[-1] if 'Total Equity Gross Minority Interest' in balance_sheet.index else 0
            else:
                total_assets = info.get('totalAssets', 0)
                total_liabilities = info.get('totalLiabilities', 0)
                total_equity = info.get('totalEquity', 0)
            
            # Nakit akışı
            cash_flow = stock.cashflow
            if not cash_flow.empty:
                operating_cash = cash_flow.loc['Operating Cash Flow'].iloc[-1] if 'Operating Cash Flow' in cash_flow.index else 0
            else:
                operating_cash = info.get('operatingCashFlow', 0)
            
            bilanco = {
                "net_kar": safe_float(net_income),
                "favok": safe_float(info.get('ebitda', 0)),
                "ciro": safe_float(total_revenue),
                "borc": safe_float(total_liabilities),
                "net_nakit": safe_float(operating_cash),
                "ozsermaye": safe_float(total_equity),
                "toplam_varlik": safe_float(total_assets),
                "brut_kar": safe_float(gross_profit),
                "roa": safe_float(info.get('returnOnAssets', 0)) * 100,
                "roe": safe_float(info.get('returnOnEquity', 0)) * 100,
                "fk": safe_float(info.get('trailingPE', 0)),
                "pddd": safe_float(info.get('priceToBook', 0)),
                "fdfavok": safe_float(info.get('enterpriseToEbitda', 0)),
            }
            
            self.cache[cache_key] = bilanco
            return bilanco
            
        except Exception as e:
            print(f"❌ {kod} bilanço verisi alınırken hata: {e}")
            return {}
    
    def get_historical_data(self, kod: str, period: str = "6mo") -> pd.DataFrame:
        """Tarihsel veriyi al"""
        ticker = self.get_ticker(kod)
        if not ticker:
            return pd.DataFrame()
        
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period=period)
            return hist
        except Exception as e:
            print(f"❌ {kod} tarihsel verisi alınırken hata: {e}")
            return pd.DataFrame()
    
    def get_tum_hisseler(self) -> List[str]:
        """Tüm hisse kodlarını döndür"""
        return list(self.bist_ticker_map.keys())
    
    def get_market_data(self) -> Dict:
        """Genel piyasa verileri"""
        try:
            # BIST 100 endeksi
            bist = yf.Ticker("XU100.IS")
            hist = bist.history(period="1d")
            
            return {
                "bist_100": hist['Close'].iloc[-1] if not hist.empty else 0,
                "bist_degisim": ((hist['Close'].iloc[-1] - hist['Open'].iloc[-1]) / hist['Open'].iloc[-1] * 100) if not hist.empty else 0,
                "hacim": hist['Volume'].iloc[-1] if not hist.empty else 0,
                "tarih": datetime.now()
            }
        except Exception as e:
            print(f"❌ Piyasa verisi alınırken hata: {e}")
            return {}
