import sys
import logging
import datetime
from config import get_client

# logging.basicConfig(level=logging.INFO)

def show_orders(symbol="BTCUSDT", limit=10):
    """
    Fetches and displays the most recent orders for a given symbol on Binance Futures.

    Parameters:
    - symbol (str): The trading pair symbol. Defaults to 'BTCUSDT'.
    - limit (int): The number of orders to fetch. Defaults to 10.

    Returns:
    - list: A list of order data if successful, None otherwise.
    """
    client = get_client()

    try:
        logging.info(f"Fetching last {limit} orders for {symbol}...")
        response = client.rest_api.all_orders(symbol=symbol, limit=limit)
        orders = response.data()
        
        print(f"\n--- RECENT ORDERS: {symbol} ---")
        # Show newest first
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
    
    if len(sys.argv) > 1 and sys.argv[1] in ["-h", "--help"]:
        print("\n--- Binance Futures Order History ---")
        print("Usage: python show_orders.py [symbol] [limit]\n")
        print("Arguments:")
        print("  [symbol] : The symbol to check (default: BTCUSDT)")
        print("  [limit]  : The number of orders to fetch (default: 10)\n")
        print("Example:")
        print("  python show_orders.py ETHUSDT 5")
        sys.exit(0)

    symbol = sys.argv[1] if len(sys.argv) > 1 else "BTCUSDT"
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    show_orders(symbol, limit=limit)
