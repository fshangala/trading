import sys
import logging
import datetime
from config import get_client
from binance_sdk_derivatives_trading_usds_futures.rest_api.models import (
    KlineCandlestickDataIntervalEnum
)

# logging.basicConfig(level=logging.INFO) # Removed to allow importing scripts to configure logging

def get_candles(symbol="BTCUSDT", interval="1h", limit=10):
    client = get_client()

    try:
        logging.info(f"Fetching {limit} candles for {symbol} ({interval})...")
        
        # Mapping string interval to Enum
        enum_map = {
            "1m": KlineCandlestickDataIntervalEnum.INTERVAL_1m,
            "3m": KlineCandlestickDataIntervalEnum.INTERVAL_3m,
            "5m": KlineCandlestickDataIntervalEnum.INTERVAL_5m,
            "15m": KlineCandlestickDataIntervalEnum.INTERVAL_15m,
            "30m": KlineCandlestickDataIntervalEnum.INTERVAL_30m,
            "1h": KlineCandlestickDataIntervalEnum.INTERVAL_1h,
            "2h": KlineCandlestickDataIntervalEnum.INTERVAL_2h,
            "4h": KlineCandlestickDataIntervalEnum.INTERVAL_4h,
            "1d": KlineCandlestickDataIntervalEnum.INTERVAL_1d,
            "1w": KlineCandlestickDataIntervalEnum.INTERVAL_1w,
            "1M": KlineCandlestickDataIntervalEnum.INTERVAL_1M
        }
        
        target_interval = enum_map.get(interval, KlineCandlestickDataIntervalEnum.INTERVAL_1h)

        response = client.rest_api.kline_candlestick_data(
            symbol=symbol,
            interval=target_interval,
            limit=limit
        )
        
        candles = response.data()
        
        print(f"\n--- CANDLE DATA: {symbol} ({interval}) ---")
        print(f"{'Time':<20} | {'High':<10} | {'Low':<10} | {'Close':<10} | {'Volume':<10}")
        print("-" * 75)
        
        for c in candles:
            # [OpenTime, Open, High, Low, Close, Volume, CloseTime, ...]
            time_str = datetime.datetime.fromtimestamp(c[0]/1000).strftime('%Y-%m-%d %H:%M')
            print(f"{time_str:<20} | {c[2]:<10} | {c[3]:<10} | {c[4]:<10} | {float(c[5]):<10.2f}")
        print("")
        
        return candles

    except Exception as e:
        logging.error(f"Failed to fetch candles: {e}")
        return None

if __name__ == "__main__":
    symbol = sys.argv[1] if len(sys.argv) > 1 else "BTCUSDT"
    interval = sys.argv[2] if len(sys.argv) > 2 else "1h"
    limit = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    
    get_candles(symbol, interval, limit)
