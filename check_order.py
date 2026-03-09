import sys
import logging
from config import get_client

# logging.basicConfig(level=logging.INFO)

def check_order(order_id, symbol="BTCUSDT"):
    """
    Queries the status of a specific order on Binance Futures.

    Parameters:
    - order_id (int/str): The Binance order ID to query.
    - symbol (str): The trading pair symbol (e.g., 'BTCUSDT'). Defaults to 'BTCUSDT'.

    Returns:
    - dict: The order status data if successful, None otherwise.
    """
    client = get_client()

    try:
        logging.info(f"Checking status for order ID: {order_id} ({symbol})")
        response = client.rest_api.query_order(
            symbol=symbol,
            order_id=int(order_id)
        )
        
        data = response.data()
        # The data is likely a model that can be converted to dict
        print(f"\n--- ORDER STATUS ---")
        print(f"Symbol: {data['symbol']}")
        print(f"Order ID: {data['orderId']}")
        print(f"Status: {data['status']}")
        print(f"Side: {data['side']}")
        print(f"Type: {data['type']}")
        print(f"Avg Price: {data['avgPrice']}")
        print(f"Executed Qty: {data['executedQty']}")
        print(f"--------------------\n")
        return data

    except Exception as e:
        logging.error(f"Failed to query order: {e}")
        return None

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) < 2:
        print("\n--- Binance Futures Order Status Check ---")
        print("Usage: python check_order.py <order_id> [symbol]\n")
        print("Arguments:")
        print("  <order_id> : The Binance order ID to check")
        print("  [symbol]   : (Optional) The symbol (default: BTCUSDT)\n")
        print("Example:")
        print("  python check_order.py 12345678 BTCUSDT")
        sys.exit(1)
    
    order_id = sys.argv[1]
    symbol = sys.argv[2] if len(sys.argv) > 2 else "BTCUSDT"
    check_order(order_id, symbol)
