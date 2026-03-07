import sys
import logging
import datetime
from config import get_client
from indicators import calculate_ema
from binance_sdk_derivatives_trading_usds_futures.rest_api.models import (
    KlineCandlestickDataIntervalEnum
)

def find_crossover(symbol="BTCUSDT", interval="1h", limit=500):
    client = get_client()

    try:
        enum_map = {
            "1m": KlineCandlestickDataIntervalEnum.INTERVAL_1m,
            "5m": KlineCandlestickDataIntervalEnum.INTERVAL_5m,
            "15m": KlineCandlestickDataIntervalEnum.INTERVAL_15m,
            "1h": KlineCandlestickDataIntervalEnum.INTERVAL_1h,
            "4h": KlineCandlestickDataIntervalEnum.INTERVAL_4h,
            "1d": KlineCandlestickDataIntervalEnum.INTERVAL_1d
        }
        
        logging.info(f"Fetching {limit} candles for {symbol} ({interval})...")
        response = client.rest_api.kline_candlestick_data(
            symbol=symbol, 
            interval=enum_map.get(interval, KlineCandlestickDataIntervalEnum.INTERVAL_1h), 
            limit=limit
        )
        candles = response.data()
        if not candles or len(candles) < 100:
            print("Not enough data to calculate EMA 99 series.")
            return

        close_prices = [float(c[4]) for c in candles]
        timestamps = [c[0] for c in candles]

        # Calculate EMA series
        ema25_series = []
        ema99_series = []

        # Optimization: We start calculating from index 99 to ensure EMA99 is ready
        # For EMA series calculation, we need enough data for the first point
        for i in range(100, len(close_prices) + 1):
            prices_subset = close_prices[:i]
            ema25_series.append(calculate_ema(prices_subset, 25))
            ema99_series.append(calculate_ema(prices_subset, 99))

        # Align timestamps with the series (starts from index 99)
        relevant_timestamps = timestamps[99:]

        # Search for crossover from newest to oldest
        found = False
        print(f"\n--- EMA 25/99 CROSSOVER ANALYSIS: {symbol} ({interval}) ---")
        
        for i in range(len(ema25_series) - 1, 0, -1):
            curr_25, curr_99 = ema25_series[i], ema99_series[i]
            prev_25, prev_99 = ema25_series[i-1], ema99_series[i-1]

            if curr_25 is None or curr_99 is None or prev_25 is None or prev_99 is None:
                continue

            # Golden Cross (25 crosses above 99)
            if prev_25 <= prev_99 and curr_25 > curr_99:
                dt = datetime.datetime.fromtimestamp(relevant_timestamps[i]/1000)
                print(f"GOLDEN CROSS found at: {dt.strftime('%Y-%m-%d %H:%M')}")
                print(f"Details: EMA25 ({curr_25:.2f}) > EMA99 ({curr_99:.2f})")
                found = True
                break
            
            # Death Cross (25 crosses below 99)
            elif prev_25 >= prev_99 and curr_25 < curr_99:
                dt = datetime.datetime.fromtimestamp(relevant_timestamps[i]/1000)
                print(f"DEATH CROSS found at:  {dt.strftime('%Y-%m-%d %H:%M')}")
                print(f"Details: EMA25 ({curr_25:.2f}) < EMA99 ({curr_99:.2f})")
                found = True
                break

        if not found:
            print(f"No crossover found in the last {limit} candles.")
        print("------------------------------------------------------\n")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    symbol = sys.argv[1] if len(sys.argv) > 1 else "BNBUSDT"
    interval = sys.argv[2] if len(sys.argv) > 2 else "1h"
    find_crossover(symbol, interval, limit=500)
