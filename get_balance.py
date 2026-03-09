import logging
import sys
from config import get_client

# logging.basicConfig(level=logging.INFO)

def get_futures_balance(asset="USDT"):
    """
    Fetches the USDS-M Futures account balance for a specific asset.

    Parameters:
    - asset (str): The asset name (e.g., 'USDT', 'BNB'). Defaults to 'USDT'.

    Returns:
    - dict: A dictionary containing 'asset', 'balance' (total), and 'available' (available margin).
            Returns None if the asset is not found or an error occurs.
    """
    client = get_client()

    try:
        logging.info(f"Fetching futures account balance for {asset}...")
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
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) > 1 and sys.argv[1] in ["-h", "--help"]:
        print("\n--- Binance Futures Balance Check ---")
        print("Usage: python get_balance.py [asset]\n")
        print("Arguments:")
        print("  [asset] : (Optional) The asset to check (default: USDT)\n")
        print("Example:")
        print("  python get_balance.py BNB")
        sys.exit(0)

    asset = sys.argv[1] if len(sys.argv) > 1 else "USDT"
    res = get_futures_balance(asset)
    
    if res:
        print(f"\n--- {res['asset']} FUTURES BALANCE ---")
        print(f"Total Balance:     {res['balance']:.2f}")
        print(f"Available/Margin:  {res['available']:.2f}")
        print("----------------------------\n")
    else:
        print(f"Asset '{asset}' not found in futures account.")
