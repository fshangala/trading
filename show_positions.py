import sys
import logging
from config import get_client

# logging.basicConfig(level=logging.INFO) # Removed to allow importing scripts to configure logging

def show_positions(symbol=None):
    """
    Fetches and displays active (non-zero) positions on the USDS-M Futures account.

    Parameters:
    - symbol (str, optional): The symbol to filter by. If None, shows all active positions.

    Returns:
    - list: A list of position data if successful, None otherwise.
    """
    client = get_client()

    try:
        logging.info(f"Fetching active positions{' for ' + symbol if symbol else ''}...")
        response = client.rest_api.position_information_v2(symbol=symbol, recv_window=10000)
        positions = response.data()
        
        # Filter and display only non-zero positions
        active_found = False
        print(f"\n--- ACTIVE POSITIONS ---")
        for pos in positions:
            # The SDK likely returns a list of dicts or models
            amt = float(pos.get("positionAmt", 0)) if isinstance(pos, dict) else float(pos.position_amt)
            if amt != 0:
                active_found = True
                if isinstance(pos, dict):
                    print(f"Symbol:     {pos.get('symbol')}")
                    print(f"Side:       {pos.get('positionSide')}")
                    print(f"Amount:     {pos.get('positionAmt')}")
                    print(f"Entry:      {pos.get('entryPrice')}")
                    print(f"Mark:       {pos.get('markPrice')}")
                    print(f"Unrealized: {pos.get('unRealizedProfit')} USDT")
                else:
                    print(f"Symbol:     {pos.symbol}")
                    print(f"Side:       {pos.position_side}")
                    print(f"Amount:     {pos.position_amt}")
                    print(f"Entry:      {pos.entry_price}")
                    print(f"Mark:       {pos.mark_price}")
                    print(f"Unrealized: {pos.un_realized_profit} USDT")
                print(f"------------------------")
        
        if not active_found:
            print("No active positions found.")
        print("")
        
        return positions

    except Exception as e:
        logging.error(f"Failed to fetch positions: {e}")
        return None

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) > 1 and sys.argv[1] in ["-h", "--help"]:
        print("\n--- Binance Futures Active Positions ---")
        print("Usage: python show_positions.py [symbol]\n")
        print("Arguments:")
        print("  [symbol] : (Optional) Filter by symbol (e.g. BTCUSDT)\n")
        sys.exit(0)

    symbol = sys.argv[1] if len(sys.argv) > 1 else None
    show_positions(symbol)
