import sys
import logging
from config import get_client

# logging.basicConfig(level=logging.INFO)

def show_protection_orders(symbol=None):
    """
    Fetches and displays all open protection (Algo) orders on Binance Futures.

    Parameters:
    - symbol (str, optional): The symbol to filter by. If None, shows all open algo orders.

    Returns:
    - list: A list of open algo order data if successful, None otherwise.
    """
    client = get_client()

    try:
        logging.info(f"Fetching open protection (algo) orders{' for ' + symbol if symbol else ''}...")
        response = client.rest_api.current_all_algo_open_orders(symbol=symbol, recv_window=10000)
        orders = response.data()
        
        print(f"\n--- OPEN PROTECTION ORDERS ---")
        if not orders:
            print("No open protection orders found.")
        else:
            for order in orders:
                # Based on the model definition, using snake_case attributes
                print(f"Symbol:    {order.symbol}")
                print(f"Algo ID:   {order.algo_id}")
                print(f"Side:      {order.side} ({order.position_side})")
                print(f"Type:      {order.order_type}")
                
                # Handling different attribute names for different algo types
                tp = getattr(order, 'trigger_price', 'N/A')
                if tp == 'N/A':
                    # For Trailing Stop, might be callbackRate or activationPrice
                    tp = f"CB: {getattr(order, 'callback_rate', 'N/A')}% / Act: {getattr(order, 'activate_price', 'N/A')}"
                
                print(f"Trigger:   {tp} ({getattr(order, 'working_type', 'N/A')})")
                print(f"Status:    {order.algo_status}")
                print(f"------------------------")
        print("")
        
        return orders

    except Exception as e:
        logging.error(f"Failed to fetch protection orders: {e}")
        return None

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) > 1 and sys.argv[1] in ["-h", "--help"]:
        print("\n--- Binance Futures Open Protection Orders ---")
        print("Usage: python show_protection_orders.py [symbol]\n")
        print("Arguments:")
        print("  [symbol] : (Optional) Filter by symbol (e.g. BTCUSDT)\n")
        sys.exit(0)

    symbol = sys.argv[1] if len(sys.argv) > 1 else None
    show_protection_orders(symbol)
