import sys
import logging
from config import get_client

# logging.basicConfig(level=logging.INFO)

def show_protection_orders(symbol=None):
    client = get_client()

    try:
        logging.info(f"Fetching open protection (algo) orders{' for ' + symbol if symbol else ''}...")
        response = client.rest_api.current_all_algo_open_orders(symbol=symbol)
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
                # Looking at common patterns, likely trigger_price or stop_price
                # Let's check common attributes from the model grep earlier
                tp = getattr(order, 'trigger_price', 'N/A')
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
    symbol = sys.argv[1] if len(sys.argv) > 1 else None
    show_protection_orders(symbol)
