import sys
import logging
from config import get_client

# logging.basicConfig(level=logging.INFO)

def cancel_protection_order(symbol, algo_id=None, client_algo_id=None):
    client = get_client()

    try:
        logging.info(f"Cancelling protection order {algo_id if algo_id else client_algo_id} for {symbol}...")
        response = client.rest_api.cancel_algo_order(
            algo_id=algo_id,
            client_algo_id=client_algo_id
        )
        
        data = response.data()
        logging.info(f"Cancellation Successful! ID: {data.algo_id}")
        return data

    except Exception as e:
        logging.error(f"Failed to cancel protection order: {e}")
        return None

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python cancel_protection.py <symbol> <algo_id>")
        sys.exit(1)
    
    symbol = sys.argv[1]
    algo_id = int(sys.argv[2])
    
    cancel_protection_order(symbol, algo_id=algo_id)
