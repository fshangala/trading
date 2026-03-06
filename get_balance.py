import logging
from config import get_config

config = get_config()
# logging.basicConfig(level=logging.INFO)

from binance_sdk_derivatives_trading_usds_futures.derivatives_trading_usds_futures import DerivativesTradingUsdsFutures
from binance_common.configuration import ConfigurationRestAPI

def get_futures_balance(asset="USDT"):
    configuration = ConfigurationRestAPI(
        api_key=config['api_key'],
        api_secret=config['api_secret'],
        base_path=config['base_path'],
    )

    client = DerivativesTradingUsdsFutures(config_rest_api=configuration)

    try:
        logging.info(f"Fetching futures account balance...")
        response = client.rest_api.futures_account_balance_v2()
        balances = response.data()
        
        for balance in balances:
            # The SDK might return objects or dicts
            curr_asset = balance.get("asset") if isinstance(balance, dict) else balance.asset
            if curr_asset == asset:
                if isinstance(balance, dict):
                    return {
                        "asset": balance.get("asset"),
                        "balance": float(balance.get("balance", 0)),
                        "available": float(balance.get("availableBalance", 0))
                    }
                else:
                    return {
                        "asset": balance.asset,
                        "balance": float(balance.balance),
                        "available": float(balance.available_balance)
                    }
        
        return None

    except Exception as e:
        logging.error(f"Failed to fetch balance: {e}")
        return None

if __name__ == "__main__":
    import sys
    asset = sys.argv[1] if len(sys.argv) > 1 else "USDT"
    res = get_futures_balance(asset)
    if res:
        print(f"\n--- {res['asset']} FUTURES BALANCE ---")
        print(f"Total Balance:     {res['balance']:.2f}")
        print(f"Available/Margin:  {res['available']:.2f}")
        print("----------------------------\n")
    else:
        print(f"Asset {asset} not found in futures account.")
