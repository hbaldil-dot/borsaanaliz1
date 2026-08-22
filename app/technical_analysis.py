# app/technical_analysis.py
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import ta

class TechnicalAnalysis:
    @staticmethod
    def calculate_all_indicators(data: pd.DataFrame) -> Dict:
        """Tüm teknik göstergeleri hesapla"""
        if data.empty:
            return {}
        
        close = data['Close']
        high = data['High']
        low = data['Low']
        volume = data['Volume']
        
        indicators = {}
        
        # Trend göstergeleri
        indicators['ema20'] = ta.trend.ema_indicator(close, window=20)
        indicators['ema50'] = ta.trend.ema_indicator(close, window=50)
        indicators['ema200'] = ta.trend.ema_indicator(close, window=200)
        
        # Momentum
        indicators['rsi'] = ta.momentum.rsi(close, window=14)
        
        # MACD
        macd = ta.trend.MACD(close)
        indicators['macd'] = macd.macd()
        indicators['macd_signal'] = macd.macd_signal()
        indicators['macd_diff'] = macd.macd_diff()
        
        # Bollinger
        bb = ta.volatility.BollingerBands(close)
        indicators['bb_upper'] = bb.bollinger_hband()
        indicators['bb_middle'] = bb.bollinger_mavg()
        indicators['bb_lower'] = bb.bollinger_lband()
        
        # Volume
        indicators['obv'] = ta.volume.OnBalanceVolumeIndicator(close, volume).on_balance_volume()
        
        # Diğer
        indicators['atr'] = ta.volatility.average_true_range(high, low, close)
        
        return indicators
    
    @staticmethod
    def get_support_resistance(data: pd.DataFrame, lookback: int = 20) -> Tuple[List[float], List[float]]:
        """Destek ve direnç seviyelerini bul"""
        high = data['High'].tail(lookback)
        low = data['Low'].tail(lookback)
        
        # Yerel zirveler
        resistance = []
        for i in range(2, len(high) - 2):
            if high.iloc[i] > high.iloc[i-1] and high.iloc[i] > high.iloc[i-2] and \
               high.iloc[i] > high.iloc[i+1] and high.iloc[i] > high.iloc[i+2]:
                resistance.append(high.iloc[i])
        
        # Yerel dipler
        support = []
        for i in range(2, len(low) - 2):
            if low.iloc[i] < low.iloc[i-1] and low.iloc[i] < low.iloc[i-2] and \
               low.iloc[i] < low.iloc[i+1] and low.iloc[i] < low.iloc[i+2]:
                support.append(low.iloc[i])
        
        # Benzersiz seviyeler
        resistance = list(set(np.round(resistance, 2)))[:5]
        support = list(set(np.round(support, 2)))[:5]
        
        return support, resistance
