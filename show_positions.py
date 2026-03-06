import sys
import os
import logging
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)

from binance_sdk_derivatives_trading_usds_futures.derivatives_trading_usds_futures import DerivativesTradingUsdsFutures
from binance_common.configuration import ConfigurationRestAPI

def show_positions(symbol=None):
    configuration = ConfigurationRestAPI(
        api_key=os.getenv("BINANCE_API_KEY", ""),
        api_secret=os.getenv("BINANCE_API_SECRET", ""),
        base_path="https://demo-fapi.binance.com/",
    )

    client = DerivativesTradingUsdsFutures(config_rest_api=configuration)

    try:
        logging.info(f"Fetching active positions{' for ' + symbol if symbol else ''}...")
        response = client.rest_api.position_information_v2(symbol=symbol)
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
    symbol = sys.argv[1] if len(sys.argv) > 1 else None
    show_positions(symbol)
