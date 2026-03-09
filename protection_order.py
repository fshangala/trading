import sys
import logging
from config import get_client

# logging.basicConfig(level=logging.INFO)

def set_protection_order(symbol, side, position_side, order_type, trigger_price=None, working_type="CONTRACT_PRICE", callback_rate=None, activate_price=None, quantity=None, close_position="true"):
    """
    Sets a protection (Algo) order on Binance Futures.

    Parameters:
    - symbol (str): The symbol to trade (e.g., 'BTCUSDT').
    - side (str): The order side ('BUY' to close a Short, 'SELL' to close a Long).
    - position_side (str): The position side in Hedge Mode ('LONG' or 'SHORT').
    - order_type (str): The protection type ('STOP', 'TP', or 'TRAILING').
    - trigger_price (float, optional): The price that triggers the Stop or TP order.
    - working_type (str, optional): Trigger source ('MARK_PRICE' or 'CONTRACT_PRICE'). Defaults to 'CONTRACT_PRICE'.
    - callback_rate (float, optional): The percentage distance (0.1 to 5.0) for Trailing Stop.
    - activate_price (float, optional): The price at which the trailing stop becomes active.
    - quantity (float, optional): The quantity to close. If not provided, close_position=true is used for STOP/TP.
    - close_position (str, optional): Set to 'true' to close the entire position (for STOP/TP). Defaults to 'true'.
    
    Note: 'algo_type' is automatically set to 'CONDITIONAL' per Binance API requirements for these order types.
    """
    client = get_client()

    # Map simple types to Binance order types
    type_map = {
        "STOP": "STOP_MARKET",
        "TP": "TAKE_PROFIT_MARKET",
        "TRAILING": "TRAILING_STOP_MARKET"
    }
    binance_type = type_map.get(order_type.upper(), "STOP_MARKET")

    try:
        logging.info(f"Setting {binance_type} (CONDITIONAL) for {symbol} {position_side}")
        
        params = {
            "algo_type": "CONDITIONAL",
            "symbol": symbol,
            "side": side,
            "position_side": position_side,
            "type": binance_type
        }
        
        # Determine if close_position or quantity should be used
        if quantity:
            params["quantity"] = float(quantity)
        else:
            # For TP/SL, close_position is standard. For Trailing, quantity is often better.
            if binance_type != "TRAILING_STOP_MARKET":
                params["close_position"] = close_position.lower()
        
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
        print("\n--- Binance Futures Protection Order Toolkit ---")
        print("Usage: python protection_order.py <symbol> <side> <pos_side> <type> [trigger/callback] [working/activate] [quantity] [close_position]\n")
        print("Arguments:")
        print("  <symbol>         : Symbol (e.g. BNBUSDT)")
        print("  <side>           : Order direction (BUY/SELL)")
        print("  <pos_side>       : Hedge Mode position side (LONG/SHORT)")
        print("  <type>           : Order type (STOP / TP / TRAILING)")
        print("  [trigger/callback] : Stop/TP Trigger Price OR Trailing Callback Rate (0.1 - 5.0)")
        print("  [working/activate] : Trigger Source (MARK_PRICE/CONTRACT_PRICE) OR Trailing Activation Price")
        print("  [quantity]       : (Optional) Exact quantity to close")
        print("  [close_position] : (Optional) 'true' or 'false' (default: true for STOP/TP)\n")
        print("Examples:")
        print("  python protection_order.py BNBUSDT SELL LONG STOP 600.00")
        print("  python protection_order.py BNBUSDT SELL LONG TRAILING 0.8 630.00 0.8")
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
        callback_rate = parse_none(sys.argv[5]) if len(sys.argv) > 5 else None
        activate_price = parse_none(sys.argv[6]) if len(sys.argv) > 6 else None
        quantity = parse_none(sys.argv[7]) if len(sys.argv) > 7 else None
        close_position = sys.argv[8] if len(sys.argv) > 8 else "true"
        set_protection_order(symbol, side, pos_side, order_type, callback_rate=callback_rate, activate_price=activate_price, quantity=quantity, close_position=close_position)
    else:
        trigger_price = parse_none(sys.argv[5]) if len(sys.argv) > 5 else None
        working_type = parse_none(sys.argv[6]) if len(sys.argv) > 6 else "CONTRACT_PRICE"
        quantity = parse_none(sys.argv[7]) if len(sys.argv) > 7 else None
        close_position = sys.argv[8] if len(sys.argv) > 8 else "true"
        set_protection_order(symbol, side, pos_side, order_type, trigger_price=trigger_price, working_type=working_type, quantity=quantity, close_position=close_position)
