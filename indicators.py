import sys
import logging
import math
from config import get_client
from binance_sdk_derivatives_trading_usds_futures.rest_api.models import (
    KlineCandlestickDataIntervalEnum
)

# logging.basicConfig(level=logging.INFO) # Removed to allow importing scripts to configure logging

def calculate_ema(prices, period):
    """
    Calculates the Exponential Moving Average (EMA) for a series of prices.
    """
    if len(prices) < period:
        return None
    multiplier = 2 / (period + 1)
    ema = sum(prices[:period]) / period
    for price in prices[period:]:
        ema = (price - ema) * multiplier + ema
    return ema

def calculate_rsi(prices, period=14):
    """
    Calculates the Relative Strength Index (RSI) for a series of prices.
    """
    if len(prices) < period + 1:
        return None
    gains = []
    losses = []
    for i in range(1, len(prices)):
        change = prices[i] - prices[i-1]
        gains.append(max(0, change))
        losses.append(max(0, -change))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0: return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calculate_macd(prices, slow=26, fast=12, signal=9):
    """
    Calculates the Moving Average Convergence Divergence (MACD) indicator.
    Returns: (macd_line, signal_line, histogram)
    """
    def get_ema_series(data, period):
        if len(data) < period: return []
        ema_series = []
        multiplier = 2 / (period + 1)
        ema = sum(data[:period]) / period
        ema_series.append(ema)
        for price in data[period:]:
            ema = (price - ema) * multiplier + ema
            ema_series.append(ema)
        return ema_series
    fast_ema = get_ema_series(prices, fast)
    slow_ema = get_ema_series(prices, slow)
    min_len = min(len(fast_ema), len(slow_ema))
    macd_line = [f - s for f, s in zip(fast_ema[-min_len:], slow_ema[-min_len:])]
    if len(macd_line) < signal: return None, None, None
    signal_line_series = get_ema_series(macd_line, signal)
    return macd_line[-1], signal_line_series[-1], macd_line[-1] - signal_line_series[-1]

def calculate_bollinger_bands(prices, period=20, std_dev_mult=2):
    """
    Calculates Bollinger Bands for a series of prices.
    Returns: (upper_band, middle_band, lower_band)
    """
    if len(prices) < period: return None, None, None
    sma = sum(prices[-period:]) / period
    variance = sum((p - sma) ** 2 for p in prices[-period:]) / period
    std_dev = math.sqrt(variance)
    return sma + (std_dev_mult * std_dev), sma, sma - (std_dev_mult * std_dev)

def calculate_atr(candles, period=14):
    """
    Calculates the Average True Range (ATR) from candlestick data.
    """
    if len(candles) < period + 1: return None
    tr_list = []
    for i in range(1, len(candles)):
        h, l, pc = float(candles[i][2]), float(candles[i][3]), float(candles[i-1][4])
        tr_list.append(max(h - l, abs(h - pc), abs(l - pc)))
    atr = sum(tr_list[:period]) / period
    for i in range(period, len(tr_list)):
        atr = (atr * (period - 1) + tr_list[i]) / period
    return atr

def calculate_obv(candles):
    """
    Calculates the On-Balance Volume (OBV) indicator.
    """
    if len(candles) < 2: return 0
    obv = 0
    for i in range(1, len(candles)):
        close, prev_close, vol = float(candles[i][4]), float(candles[i-1][4]), float(candles[i][5])
        if close > prev_close: obv += vol
        elif close < prev_close: obv -= vol
    return obv

def calculate_vwap(candles):
    """
    Calculates the Volume Weighted Average Price (VWAP).
    """
    total_pv = 0
    total_volume = 0
    for c in candles:
        h, l, cl, v = float(c[2]), float(c[3]), float(c[4]), float(c[5])
        total_pv += ((h + l + cl) / 3) * v
        total_volume += v
    return total_pv / total_volume if total_volume != 0 else 0

def get_indicators(symbol="BTCUSDT", interval="1h"):
    """
    Fetches candlestick data and calculates a suite of technical indicators for a symbol.

    Parameters:
    - symbol (str): The trading pair symbol.
    - interval (str): The timeframe (e.g. '15m', '1h').

    Returns:
    - dict: A dictionary containing calculated indicators and current price.
    """
    client = get_client()
    try:
        limit = 200
        enum_map = {"1m": KlineCandlestickDataIntervalEnum.INTERVAL_1m, "3m": KlineCandlestickDataIntervalEnum.INTERVAL_3m, "5m": KlineCandlestickDataIntervalEnum.INTERVAL_5m, "15m": KlineCandlestickDataIntervalEnum.INTERVAL_15m, "30m": KlineCandlestickDataIntervalEnum.INTERVAL_30m, "1h": KlineCandlestickDataIntervalEnum.INTERVAL_1h, "4h": KlineCandlestickDataIntervalEnum.INTERVAL_4h, "1d": KlineCandlestickDataIntervalEnum.INTERVAL_1d}
        response = client.rest_api.kline_candlestick_data(symbol=symbol, interval=enum_map.get(interval, KlineCandlestickDataIntervalEnum.INTERVAL_1h), limit=limit)
        candles = response.data()
        if not candles: return None
        close_prices = [float(c[4]) for c in candles]
        current_price = close_prices[-1]
        
        res = {
            "price": current_price,
            "ema7": calculate_ema(close_prices, 7),
            "ema25": calculate_ema(close_prices, 25),
            "ema99": calculate_ema(close_prices, 99),
            "vwap": calculate_vwap(candles),
            "rsi": calculate_rsi(close_prices),
            "macd": calculate_macd(close_prices),
            "bb": calculate_bollinger_bands(close_prices),
            "atr": calculate_atr(candles),
            "obv": calculate_obv(candles)
        }

        print(f"\n--- INDICATORS: {symbol} ({interval}) ---")
        print(f"Price: {res['price']:.6f} | RSI: {res['rsi']:.2f}" if res['rsi'] else f"Price: {res['price']:.6f}")
        print(f"EMA 7/25/99: {res['ema7']:.6f} / {res['ema25']:.6f} / {res['ema99']:.6f}")
        if res['macd'][0]: print(f"MACD: {res['macd'][0]:.6f} | Signal: {res['macd'][1]:.6f} | Hist: {res['macd'][2]:.6f}")
        if res['bb'][0]: print(f"Bollinger: U {res['bb'][0]:.6f} | M {res['bb'][1]:.6f} | L {res['bb'][2]:.6f}")
        if res['atr']: print(f"ATR: {res['atr']:.6f} | VWAP: {res['vwap']:.6f} | OBV: {res['obv']:.0f}")
        
        signals = []
        if res['ema7'] > res['ema25']: signals.append("BULLISH (EMA 7>25)")
        else: signals.append("BEARISH (EMA 7<25)")
        if res['rsi']:
            if res['rsi'] > 70: signals.append("OVERBOUGHT (RSI)")
            elif res['rsi'] < 30: signals.append("OVERSOLD (RSI)")
        if res['macd'][2]:
            if res['macd'][2] > 0: signals.append("MOMENTUM UP (MACD)")
            else: signals.append("MOMENTUM DOWN (MACD)")
        
        print(f"Signals: {', '.join(signals)}")
        print("------------------------------------\n")
        return res
    except Exception as e:
        logging.error(f"Error calculating indicators: {e}")
        return None

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) > 1 and sys.argv[1] in ["-h", "--help"]:
        print("\n--- Technical Indicators Analysis ---")
        print("Usage: python indicators.py [symbol] [interval]\n")
        print("Arguments:")
        print("  [symbol]   : The symbol to analyze (default: BTCUSDT)")
        print("  [interval] : Timeframe: 1m, 3m, 5m, 15m, 30m, 1h, 4h, 1d (default: 1h)\n")
        print("Example:")
        print("  python indicators.py ETHUSDT 15m")
        sys.exit(0)

    symbol = sys.argv[1] if len(sys.argv) > 1 else "BTCUSDT"
    interval = sys.argv[2] if len(sys.argv) > 2 else "1h"
    get_indicators(symbol, interval)
