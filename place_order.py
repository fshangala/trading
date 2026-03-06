import sys
import os
import logging
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)

from binance_sdk_derivatives_trading_usds_futures.derivatives_trading_usds_futures import DerivativesTradingUsdsFutures
from binance_sdk_derivatives_trading_usds_futures.rest_api.models import (
    NewOrderSideEnum,
    NewOrderPositionSideEnum
)
from binance_common.configuration import ConfigurationRestAPI

def place_order(symbol, side, order_type, quantity, position_side, price=None):
    configuration = ConfigurationRestAPI(
        api_key=os.getenv("BINANCE_API_KEY", ""),
        api_secret=os.getenv("BINANCE_API_SECRET", ""),
        base_path="https://demo-fapi.binance.com/",
    )

    client = DerivativesTradingUsdsFutures(config_rest_api=configuration)

    try:
        logging.info(f"Placing {order_type} order: {side} {quantity} {symbol} ({position_side})")
        
        params = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": float(quantity),
            "position_side": position_side
        }
        
        if price:
            params["price"] = float(price)
            params["time_in_force"] = "GTC" # Good Till Cancelled is standard for limit orders

        response = client.rest_api.new_order(**params)
        
        data = response.data()
        logging.info(f"Order Successful! ID: {data.order_id}, Status: {data.status}")
        return data

    except Exception as e:
        logging.error(f"Failed to place order: {e}")
        return None

if __name__ == "__main__":
    if len(sys.argv) < 6:
        print("Usage: python place_order.py <symbol> <side:BUY|SELL> <type:MARKET|LIMIT> <quantity> <pos_side:LONG|SHORT|BOTH> [price]")
        sys.exit(1)
    
    symbol = sys.argv[1]
    side = sys.argv[2]
    order_type = sys.argv[3]
    quantity = sys.argv[4]
    pos_side = sys.argv[5]
    price = sys.argv[6] if len(sys.argv) > 6 else None
    
    place_order(symbol, side, order_type, quantity, pos_side, price)
