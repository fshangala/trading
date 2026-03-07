import sys
import logging
from config import get_client

# logging.basicConfig(level=logging.INFO)

def set_protection_order(symbol, side, position_side, order_type, trigger_price=None, working_type="CONTRACT_PRICE", callback_rate=None, activate_price=None, quantity=None):
    client = get_client()

    # Map simple types to Binance order types
    type_map = {
        "STOP": "STOP_MARKET",
        "TP": "TAKE_PROFIT_MARKET",
        "TRAILING": "TRAILING_STOP_MARKET"
    }
    binance_type = type_map.get(order_type.upper(), "STOP_MARKET")

    try:
        logging.info(f"Setting {binance_type} for {symbol} {position_side}")
        
        params = {
            "algo_type": "CONDITIONAL",
            "symbol": symbol,
            "side": side,
            "position_side": position_side,
            "type": binance_type
        }
        
        # TRAILING_STOP_MARKET often doesn't support close_position=true in algo orders
        if binance_type != "TRAILING_STOP_MARKET":
            params["close_position"] = "true"
        elif quantity:
            params["quantity"] = float(quantity)
        
        if trigger_price:
            params["trigger_price"] = float(trigger_price)
            params["working_type"] = working_type
            
        if callback_rate:
            params["callback_rate"] = float(callback_rate)
            
        if activate_price:
            params["activate_price"] = float(activate_price)

        response = client.rest_api.new_algo_order(**params)
        
        data = response.data()
        logging.info(f"Protection Order Successful! ID: {data.algo_id}")
        return data

    except Exception as e:
        logging.error(f"Failed to set protection order: {e}")
        return None

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 5:
        print("Usage: python protection_order.py <symbol> <side:BUY|SELL> <pos_side:LONG|SHORT|BOTH> <type:STOP|TP|TRAILING> [trigger_price/callback_rate] [working_type/activate_price] [quantity]")
        sys.exit(1)
    
    symbol = sys.argv[1]
    side = sys.argv[2]
    pos_side = sys.argv[3]
    order_type = sys.argv[4]
    
    def parse_none(val):
        if val is None or val.lower() == "none":
            return None
        return val

    if order_type.upper() == "TRAILING":
        callback_rate = parse_none(sys.argv[5])
        activate_price = parse_none(sys.argv[6]) if len(sys.argv) > 6 else None
        quantity = parse_none(sys.argv[7]) if len(sys.argv) > 7 else None
        set_protection_order(symbol, side, pos_side, order_type, callback_rate=callback_rate, activate_price=activate_price, quantity=quantity)
    else:
        trigger_price = parse_none(sys.argv[5])
        working_type = parse_none(sys.argv[6]) if len(sys.argv) > 6 else "CONTRACT_PRICE"
        set_protection_order(symbol, side, pos_side, order_type, trigger_price=trigger_price, working_type=working_type)
