import sys
import logging
from config import get_client

# logging.basicConfig(level=logging.INFO)

def cancel_protection_order(symbol, algo_id=None, client_algo_id=None):
    """
    Cancels an active protection (Algo) order on Binance Futures.

    Parameters:
    - symbol (str): The trading pair symbol (e.g., 'BTCUSDT').
    - algo_id (int/str, optional): The Binance algo ID to cancel.
    - client_algo_id (str, optional): The client-side algo ID to cancel.

    Returns:
    - dict: The cancellation response data if successful, None otherwise.
    """
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
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) < 3:
        print("\n--- Binance Futures Protection Order Cancellation ---")
        print("Usage: python cancel_protection.py <symbol> <algo_id>\n")
        print("Arguments:")
        print("  <symbol>  : The symbol (e.g. BTCUSDT)")
        print("  <algo_id> : The Binance algo ID to cancel\n")
        print("Example:")
        print("  python cancel_protection.py BTCUSDT 200000012345")
        sys.exit(1)
    
    symbol = sys.argv[1]
    algo_id = int(sys.argv[2])
    
    cancel_protection_order(symbol, algo_id=algo_id)
