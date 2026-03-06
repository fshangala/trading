import sys
import os
import logging
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)

from binance_sdk_derivatives_trading_usds_futures.derivatives_trading_usds_futures import DerivativesTradingUsdsFutures
from binance_common.configuration import ConfigurationRestAPI

def cancel_protection_order(symbol, algo_id=None, client_algo_id=None):
    configuration = ConfigurationRestAPI(
        api_key=os.getenv("BINANCE_API_KEY", ""),
        api_secret=os.getenv("BINANCE_API_SECRET", ""),
        base_path="https://demo-fapi.binance.com/",
    )

    client = DerivativesTradingUsdsFutures(config_rest_api=configuration)

    try:
        logging.info(f"Cancelling protection order {algo_id if algo_id else client_algo_id}...")
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
