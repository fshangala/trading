import sys
import logging
from config import get_client

# logging.basicConfig(level=logging.INFO)

def cancel_order(symbol, order_id=None, client_order_id=None):
    client = get_client()

    try:
        logging.info(f"Cancelling order {order_id if order_id else client_order_id} for {symbol}...")
        params = {"symbol": symbol}
        if order_id:
            params["order_id"] = int(order_id)
        if client_order_id:
            params["client_order_id"] = client_order_id
            
        response = client.rest_api.cancel_order(**params)
        
        data = response.data()
        logging.info(f"Cancellation Successful! ID: {data.order_id}, Status: {data.status}")
        return data

    except Exception as e:
        logging.error(f"Failed to cancel order: {e}")
        return None

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) < 3:
        print("Usage: python cancel_order.py <symbol> <order_id>")
        sys.exit(1)
    
    symbol = sys.argv[1]
    order_id = sys.argv[2]
    
    cancel_order(symbol, order_id=order_id)
