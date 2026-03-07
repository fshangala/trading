import sys
import logging
import datetime
from config import get_client

# logging.basicConfig(level=logging.INFO)

def show_orders(symbol="BTCUSDT", limit=10):
    client = get_client()

    try:
        logging.info(f"Fetching last {limit} orders for {symbol}...")
        response = client.rest_api.all_orders(symbol=symbol, limit=limit)
        orders = response.data()
        
        print(f"\n--- RECENT ORDERS: {symbol} ---")
        # Reverse to show newest first
        for order in reversed(orders):
            print(f"ID:      {order.order_id}")
            print(f"Status:  {order.status}")
            print(f"Side:    {order.side} ({order.position_side})")
            print(f"Type:    {order.type} (Orig: {order.orig_type})")
            print(f"Price:   {order.price} (Avg: {order.avg_price})")
            print(f"Qty:     {order.executed_qty} / {order.orig_qty}")
            
            time_str = datetime.datetime.fromtimestamp(order.time/1000).strftime('%Y-%m-%d %H:%M:%S')
            print(f"Time:    {time_str}")
            print(f"------------------------")
        print("")
        
        return orders

    except Exception as e:
        logging.error(f"Failed to fetch orders: {e}")
        return None

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    symbol = sys.argv[1] if len(sys.argv) > 1 else "BTCUSDT"
    show_orders(symbol)
