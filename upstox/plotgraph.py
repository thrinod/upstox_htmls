
import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from datetime import datetime, timedelta
import time

# Configuration
ACCESS_TOKEN = 'eyJ0eXAiOiJKV1QiLCJrZXlfaWQiOiJza192MS4wIiwiYWxnIjoiSFMyNTYifQ.eyJzdWIiOiI0TkJWWkUiLCJqdGkiOiI2OGYwNzgyNzRmZDU3YzRhYjkxY2JlMDgiLCJpc011bHRpQ2xpZW50IjpmYWxzZSwiaXNQbHVzUGxhbiI6ZmFsc2UsImlhdCI6MTc2MDU4OTg2MywiaXNzIjoidWRhcGktZ2F0ZXdheS1zZXJ2aWNlIiwiZXhwIjoxNzYwNjUyMDAwfQ.rshmgSkF_Yvj1cxPrHiXuJFPKpimaL8c5EJDoU5s1G8'  # Replace with your access token
INSTRUMENT_KEY = 'NSE_INDEX|Nifty 50'  # NIFTY 50 instrument key

class UpstoxNiftyAnalyzer:
    def __init__(self, access_token):
        self.access_token = access_token
        self.base_url = 'https://api.upstox.com/v2'
        self.headers = {
            'Accept': 'application/json',
            'Authorization': f'Bearer {access_token}'
        }
        self.data = pd.DataFrame()
        
    def get_historical_data(self, instrument_key, interval='5minute', days=5):
        """Fetch historical data for technical indicators"""
        to_date = datetime.now()
        from_date = to_date - timedelta(days=days)
        
        url = f'{self.base_url}/historical-candle/{instrument_key}/{interval}/{to_date.strftime("%Y-%m-%d")}/{from_date.strftime("%Y-%m-%d")}'
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            
            if data['status'] == 'success' and 'data' in data:
                candles = data['data']['candles']
                df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'oi'])
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df = df.sort_values('timestamp')
                return df
        except Exception as e:
            print(f"Error fetching historical data: {e}")
            return pd.DataFrame()
    
    def get_live_quote(self, instrument_key):
        """Fetch live market quote"""
        url = f'{self.base_url}/market-quote/quotes'
        params = {'instrument_key': instrument_key}
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data['status'] == 'success':
                quote = data['data'][instrument_key]
                return {
                    'timestamp': datetime.now(),
                    'open': quote['ohlc']['open'],
                    'high': quote['ohlc']['high'],
                    'low': quote['ohlc']['low'],
                    'close': quote['last_price'],
                    'volume': quote['volume']
                }
        except Exception as e:
            print(f"Error fetching live quote: {e}")
            return None
    
    def calculate_sma(self, data, period):
        """Calculate Simple Moving Average"""
        return data['close'].rolling(window=period).mean()
    
    def calculate_bollinger_bands(self, data, period=20, std_dev=2):
        """Calculate Bollinger Bands"""
        sma = data['close'].rolling(window=period).mean()
        std = data['close'].rolling(window=period).std()
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        return sma, upper_band, lower_band
    
    def calculate_stochastic_rsi(self, data, period=14, smooth_k=3, smooth_d=3):
        """Calculate Stochastic RSI"""
        # Calculate RSI
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        # Calculate Stochastic of RSI
        rsi_min = rsi.rolling(window=period).min()
        rsi_max = rsi.rolling(window=period).max()
        stoch_rsi = ((rsi - rsi_min) / (rsi_max - rsi_min)) * 100
        
        # Smooth with SMA
        k_line = stoch_rsi.rolling(window=smooth_k).mean()
        d_line = k_line.rolling(window=smooth_d).mean()
        
        return k_line, d_line
    
    def calculate_dmi(self, data, period=14):
        """Calculate Directional Movement Index (DMI)"""
        high = data['high']
        low = data['low']
        close = data['close']
        
        # Calculate True Range
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        # Calculate Directional Movement
        up_move = high - high.shift()
        down_move = low.shift() - low
        
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
        
        plus_dm_series = pd.Series(plus_dm, index=data.index).rolling(window=period).mean()
        minus_dm_series = pd.Series(minus_dm, index=data.index).rolling(window=period).mean()
        
        # Calculate DI+ and DI-
        plus_di = 100 * (plus_dm_series / atr)
        minus_di = 100 * (minus_dm_series / atr)
        
        # Calculate ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean()
        
        return plus_di, minus_di, adx
    
    def update_data(self):
        """Update data with live quote"""
        live_quote = self.get_live_quote(INSTRUMENT_KEY)
        if live_quote:
            new_row = pd.DataFrame([live_quote])
            self.data = pd.concat([self.data, new_row], ignore_index=True)
            # Keep only last 200 data points
            if len(self.data) > 200:
                self.data = self.data.iloc[-200:]
            return True
        return False

# Initialize
analyzer = UpstoxNiftyAnalyzer(ACCESS_TOKEN)

# Fetch initial historical data
print("Fetching historical data...")
analyzer.data = analyzer.get_historical_data(INSTRUMENT_KEY, interval='5minute', days=5)

if analyzer.data.empty:
    print("Failed to fetch historical data. Please check your access token and internet connection.")
    exit()

print(f"Loaded {len(analyzer.data)} historical data points")

# Setup the plot
fig = plt.figure(figsize=(16, 10))
gs = fig.add_gridspec(5, 1, hspace=0.3)

ax1 = fig.add_subplot(gs[0:2, 0])  # Price and Bollinger Bands
ax2 = fig.add_subplot(gs[2, 0], sharex=ax1)  # Stochastic RSI
ax3 = fig.add_subplot(gs[3, 0], sharex=ax1)  # DMI
ax4 = fig.add_subplot(gs[4, 0], sharex=ax1)  # Volume

def animate(frame):
    """Animation function to update plot"""
    # Update data
    analyzer.update_data()
    data = analyzer.data.copy()
    
    if len(data) < 20:
        return
    
    # Calculate indicators
    sma20 = analyzer.calculate_sma(data, 20)
    bb_middle, bb_upper, bb_lower = analyzer.calculate_bollinger_bands(data, 20)
    stoch_k, stoch_d = analyzer.calculate_stochastic_rsi(data, 14)
    plus_di, minus_di, adx = analyzer.calculate_dmi(data, 14)
    
    # Clear all axes
    ax1.clear()
    ax2.clear()
    ax3.clear()
    ax4.clear()
    
    # Plot 1: Price with Bollinger Bands and MCD (SMA20)
    ax1.plot(data.index, data['close'], label='Close Price', color='black', linewidth=1.5)
    ax1.plot(data.index, sma20, label='SMA(20)', color='blue', linewidth=1, linestyle='--')
    ax1.plot(data.index, bb_upper, label='BB Upper', color='red', linewidth=0.8, linestyle=':')
    ax1.plot(data.index, bb_middle, label='BB Middle', color='orange', linewidth=0.8, linestyle=':')
    ax1.plot(data.index, bb_lower, label='BB Lower', color='green', linewidth=0.8, linestyle=':')
    ax1.fill_between(data.index, bb_upper, bb_lower, alpha=0.1, color='gray')
    ax1.set_ylabel('Price', fontsize=10)
    ax1.set_title(f'NIFTY 50 - Live Chart with Technical Indicators (Updated: {datetime.now().strftime("%H:%M:%S")})', 
                  fontsize=12, fontweight='bold')
    ax1.legend(loc='upper left', fontsize=8)
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Stochastic RSI
    ax2.plot(data.index, stoch_k, label='Stoch RSI %K', color='blue', linewidth=1)
    ax2.plot(data.index, stoch_d, label='Stoch RSI %D', color='red', linewidth=1)
    ax2.axhline(y=80, color='r', linestyle='--', linewidth=0.8, alpha=0.5)
    ax2.axhline(y=20, color='g', linestyle='--', linewidth=0.8, alpha=0.5)
    ax2.fill_between(data.index, 80, 100, alpha=0.1, color='red')
    ax2.fill_between(data.index, 0, 20, alpha=0.1, color='green')
    ax2.set_ylabel('Stoch RSI', fontsize=10)
    ax2.set_ylim([0, 100])
    ax2.legend(loc='upper left', fontsize=8)
    ax2.grid(True, alpha=0.3)
    
    # Plot 3: DMI (Directional Movement Index)
    ax3.plot(data.index, plus_di, label='+DI', color='green', linewidth=1)
    ax3.plot(data.index, minus_di, label='-DI', color='red', linewidth=1)
    ax3.plot(data.index, adx, label='ADX', color='blue', linewidth=1.5)
    ax3.axhline(y=25, color='gray', linestyle='--', linewidth=0.8, alpha=0.5)
    ax3.set_ylabel('DMI', fontsize=10)
    ax3.legend(loc='upper left', fontsize=8)
    ax3.grid(True, alpha=0.3)
    
    # Plot 4: Volume
    colors = ['green' if data['close'].iloc[i] >= data['open'].iloc[i] else 'red' 
              for i in range(len(data))]
    ax4.bar(data.index, data['volume'], color=colors, alpha=0.5, width=0.8)
    ax4.set_ylabel('Volume', fontsize=10)
    ax4.set_xlabel('Data Points', fontsize=10)
    ax4.grid(True, alpha=0.3)
    
    # Adjust layout
    plt.tight_layout()

# Create animation (updates every 5 seconds = 5000 milliseconds)
anim = FuncAnimation(fig, animate, interval=5000, cache_frame_data=False)

plt.show()