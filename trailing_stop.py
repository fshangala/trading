import sys
import os
import logging
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)

from binance_sdk_derivatives_trading_usds_futures.derivatives_trading_usds_futures import DerivativesTradingUsdsFutures
from binance_common.configuration import ConfigurationRestAPI

def set_trailing_stop(symbol, side, quantity, pos_side, callback_rate, activation_price=None):
    configuration = ConfigurationRestAPI(
        api_key=os.getenv("BINANCE_API_KEY", ""),
        api_secret=os.getenv("BINANCE_API_SECRET", ""),
        base_path="https://demo-fapi.binance.com/",
    )

    client = DerivativesTradingUsdsFutures(config_rest_api=configuration)

    try:
        logging.info(f"Setting TRAILING_STOP_MARKET for {symbol} {pos_side}: {side} {quantity} with {callback_rate}% callback")
        
        params = {
            "symbol": symbol,
            "side": side,
            "type": "TRAILING_STOP_MARKET",
            "quantity": float(quantity),
            "position_side": pos_side,
            "callback_rate": float(callback_rate),
            "reduce_only": "true"
        }
        
        if activation_price:
            params["activation_price"] = float(activation_price)

        response = client.rest_api.new_order(**params)
        
        data = response.data()
        logging.info(f"Trailing Stop Order Successful! ID: {data.order_id}, Status: {data.status}")
        return data

    except Exception as e:
        logging.error(f"Failed to set trailing stop: {e}")
        return None

if __name__ == "__main__":
    if len(sys.argv) < 6:
        print("Usage: python trailing_stop.py <symbol> <side:BUY|SELL> <quantity> <pos_side:LONG|SHORT|BOTH> <callback_rate:0.1-5.0> [activation_price]")
        sys.exit(1)
    
    symbol = sys.argv[1]
    side = sys.argv[2]
    quantity = sys.argv[3]
    pos_side = sys.argv[4]
    callback_rate = sys.argv[5]
    activation_price = sys.argv[6] if len(sys.argv) > 6 else None
    
    set_trailing_stop(symbol, side, quantity, pos_side, callback_rate, activation_price)
