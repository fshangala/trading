import sys
import logging
from config import get_client

# logging.basicConfig(level=logging.INFO)

def place_order(symbol, side, order_type, quantity, position_side, price=None, callback_rate=None, activation_price=None):
    """
    Places a new order (Market, Limit, or Trailing Stop) on Binance Futures.

    Parameters:
    - symbol (str): The trading pair symbol.
    - side (str): 'BUY' or 'SELL'.
    - order_type (str): 'MARKET', 'LIMIT', or 'TRAILING_STOP_MARKET'.
    - quantity (float): The amount to trade.
    - position_side (str): 'LONG', 'SHORT', or 'BOTH' (Hedge Mode).
    - price (float, optional): The price for LIMIT orders.
    - callback_rate (float, optional): Callback rate for Trailing Stop (0.1 to 5.0).
    - activation_price (float, optional): Activation price for Trailing Stop.

    Returns:
    - dict: The order response data if successful, None otherwise.
    """
    client = get_client()

    try:
        logging.info(f"Placing {order_type} order: {side} {quantity} {symbol} ({position_side})")
        
        params = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": float(quantity),
            "position_side": position_side
        }
        
        if order_type.upper() == "LIMIT" and price:
            params["price"] = float(price)
            params["time_in_force"] = "GTC"
            
        if order_type.upper() == "TRAILING_STOP_MARKET":
            if callback_rate:
                params["callback_rate"] = float(callback_rate)
            if activation_price:
                params["activation_price"] = float(activation_price)
            params["reduce_only"] = "true"

        response = client.rest_api.new_order(**params, recv_window=10000)
        
        data = response.data()
        logging.info(f"Order Successful! ID: {data.order_id}, Status: {data.status}")
        return data

    except Exception as e:
        logging.error(f"Failed to place order: {e}")
        return None

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 6:
        print("\n--- Binance Futures Order Placement ---")
        print("Usage: python place_order.py <symbol> <side> <type> <quantity> <pos_side> [price/callback] [activation]\n")
        print("Arguments:")
        print("  <symbol>    : Symbol (e.g. BTCUSDT)")
        print("  <side>      : BUY or SELL")
        print("  <type>      : MARKET, LIMIT, or TRAILING_STOP_MARKET")
        print("  <quantity>  : Amount to trade")
        print("  <pos_side>  : LONG, SHORT, or BOTH")
        print("  [price/callback] : Price for LIMIT OR Callback Rate for Trailing")
        print("  [activation]     : Activation Price for Trailing\n")
        print("Examples:")
        print("  python place_order.py BTCUSDT BUY MARKET 0.001 LONG")
        print("  python place_order.py BTCUSDT SELL TRAILING_STOP_MARKET 0.001 LONG 0.8 65000")
        sys.exit(1)
    
    symbol = sys.argv[1]
    side = sys.argv[2]
    order_type = sys.argv[3]
    quantity = sys.argv[4]
    pos_side = sys.argv[5]
    
    p1 = sys.argv[6] if len(sys.argv) > 6 else None
    p2 = sys.argv[7] if len(sys.argv) > 7 else None
    
    if order_type.upper() == "TRAILING_STOP_MARKET":
        place_order(symbol, side, order_type, quantity, pos_side, callback_rate=p1, activation_price=p2)
    else:
        place_order(symbol, side, order_type, quantity, pos_side, price=p1)
