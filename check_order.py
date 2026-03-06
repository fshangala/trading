import sys
import os
import logging
import json
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)

from binance_sdk_derivatives_trading_usds_futures.derivatives_trading_usds_futures import DerivativesTradingUsdsFutures
from binance_common.configuration import ConfigurationRestAPI

def check_order(order_id, symbol="BTCUSDT"):
    configuration = ConfigurationRestAPI(
        api_key=os.getenv("BINANCE_API_KEY", ""),
        api_secret=os.getenv("BINANCE_API_SECRET", ""),
        base_path="https://demo-fapi.binance.com/",
    )

    client = DerivativesTradingUsdsFutures(config_rest_api=configuration)

    try:
        logging.info(f"Checking status for order ID: {order_id} ({symbol})")
        response = client.rest_api.query_order(
            symbol=symbol,
            order_id=int(order_id)
        )
        
        data = response.data()
        # The data is likely a model that can be converted to dict
        print(f"\n--- ORDER STATUS ---")
        print(f"Symbol: {data['symbol']}")
        print(f"Order ID: {data['orderId']}")
        print(f"Status: {data['status']}")
        print(f"Side: {data['side']}")
        print(f"Type: {data['type']}")
        print(f"Avg Price: {data['avgPrice']}")
        print(f"Executed Qty: {data['executedQty']}")
        print(f"--------------------\n")
        return data

    except Exception as e:
        logging.error(f"Failed to query order: {e}")
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_order.py <order_id> [symbol]")
        sys.exit(1)
    
    order_id = sys.argv[1]
    symbol = sys.argv[2] if len(sys.argv) > 2 else "BTCUSDT"
    check_order(order_id, symbol)
