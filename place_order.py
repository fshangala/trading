import sys
import logging
from config import get_client

# logging.basicConfig(level=logging.INFO)

def place_order(symbol, side, order_type, quantity, position_side, price=None):
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
    logging.basicConfig(level=logging.INFO)

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
