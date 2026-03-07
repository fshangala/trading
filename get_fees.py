import sys
import logging
from config import get_client

# logging.basicConfig(level=logging.INFO)

def calculate_fees(entry_price, exit_price, quantity, symbol="BTCUSDT"):
    client = get_client()

    try:
        # Fetch current commission rates from your account
        response = client.rest_api.user_commission_rate(symbol=symbol)
        rates = response.data()
        
        # Accessing via attribute as the model is not subscriptable
        taker_rate = float(rates.taker_commission_rate)
        maker_rate = float(rates.maker_commission_rate)
        
        logging.info(f"Commission Rates for {symbol}: Taker={taker_rate*100}%, Maker={maker_rate*100}%")

        # Since we used MARKET orders, we use Taker rates for both sides
        fee_open = entry_price * quantity * taker_rate
        fee_close = exit_price * quantity * taker_rate
        total_fees = fee_open + fee_close

        print(f"\n--- FEE ANALYSIS ---")
        print(f"Opening Fee:  {fee_open:.6f} USDT")
        print(f"Closing Fee:  {fee_close:.6f} USDT")
        print(f"Total Fees:   {total_fees:.6f} USDT")
        print(f"--------------------\n")
        
        return total_fees

    except Exception as e:
        logging.error(f"Error calculating fees: {e}")
        # Fallback to standard 0.05% taker fee if API call fails
        standard_taker = 0.0005
        estimated = (entry_price + exit_price) * quantity * standard_taker
        print(f"\n--- ESTIMATED FEES (Standard 0.05%) ---")
        print(f"Estimated Total: {estimated:.6f} USDT")
        print(f"---------------------------------------\n")
        return estimated

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python get_fees.py <entry_price> <exit_price> <quantity> [symbol]")
        sys.exit(1)
    
    entry = float(sys.argv[1])
    exit_p = float(sys.argv[2])
    qty = float(sys.argv[3])
    symbol = sys.argv[4] if len(sys.argv) > 4 else "BTCUSDT"
    
    calculate_fees(entry, exit_p, qty, symbol)
