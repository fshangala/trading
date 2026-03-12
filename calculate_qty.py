import sys
import logging
from config import get_client
from get_balance import get_futures_balance
from indicators import get_indicators

def get_symbol_data(symbol):
    """
    Fetches exchange information and current price for a specific symbol.

    Parameters:
    - symbol (str): The trading pair symbol (e.g., 'BTCUSDT').

    Returns:
    - dict: A dictionary containing 'precision', 'price', and 'min_qty' if successful, None otherwise.
    """
    client = get_client()
    try:
        resp = client.rest_api.exchange_information()
        data_dict = resp.data().to_dict()
        symbols = data_dict.get("symbols", [])
        symbol_info = next((s for s in symbols if s["symbol"] == symbol.upper()), None)
        
        if not symbol_info:
            logging.error(f"Symbol {symbol} not found in exchange info.")
            return None
            
        price_resp = client.rest_api.symbol_price_ticker(symbol=symbol.upper())
        price_data = price_resp.data().to_dict()
        current_price = float(price_data.get("price", 0))
        
        lot_size_filter = next((f for f in symbol_info["filters"] if f["filterType"] == "LOT_SIZE"), None)
        min_qty = float(lot_size_filter["minQty"]) if lot_size_filter else 0
        
        return {
            "precision": int(symbol_info["quantityPrecision"]),
            "price": current_price,
            "min_qty": min_qty
        }
    except Exception as e:
        logging.error(f"Error fetching symbol data: {e}")
        return None

def calculate_quantity_fixed_margin(symbol, leverage, pos_side, margin_percent=40.0, hedge_atr_multiplier=0.5):
    """
    Calculates the quantity to trade based on a fixed margin percentage of total equity.
    Formula: Quantity = (Balance * Margin % * Leverage) / Current Price

    Parameters:
    - symbol (str): The trading pair symbol (e.g., 'BTCUSDT').
    - leverage (float): The leverage to apply (Capped at 20x).
    - pos_side (str): The position side ('LONG' or 'SHORT').
    - margin_percent (float): The percentage of total equity to use as initial margin (default 40.0).
    - hedge_atr_multiplier (float): The ATR multiplier for the Hedge distance (default 0.5).

    Returns:
    - float: The calculated quantity, or None if an error occurs.
    """
    # 1. Get Balance
    balance_data = get_futures_balance("USDT")
    if not balance_data:
        logging.error("Could not fetch USDT balance.")
        return
    
    balance = balance_data["balance"]
    
    # 2. Safety Check: Max Leverage 20x
    if leverage > 20:
        logging.warning(f"Leverage {leverage}x exceeds 20x cap. Reducing to 20x.")
        leverage = 20
    
    # 3. Get Price and ATR
    indicators = get_indicators(symbol, "15m")
    if not indicators:
        logging.error("Could not fetch indicators.")
        return
    
    current_price = indicators["price"]
    atr = indicators["atr"]
    
    # 4. Get Symbol Data
    sym_data = get_symbol_data(symbol)
    if not sym_data: return
    precision = sym_data["precision"]
    min_qty = sym_data["min_qty"]
    
    # 5. MARGIN-BASED CALCULATION
    # Target Margin = Balance * (Margin % / 100)
    target_margin = balance * (margin_percent / 100)
    
    # Quantity = (Target Margin * Leverage) / Current Price
    raw_qty = (target_margin * leverage) / current_price
    
    # 6. Rounding and Min Qty Check
    final_qty = round(raw_qty, precision)
    
    if final_qty < min_qty:
        logging.warning(f"Calculated quantity {final_qty} is below minimum {min_qty}.")
        final_qty = min_qty

    # 7. Hedge and Risk Analysis
    hedge_distance = atr * hedge_atr_multiplier
    if pos_side.upper() == "LONG":
        hedge_trigger_price = current_price - hedge_distance
    else:
        hedge_trigger_price = current_price + hedge_distance
        
    actual_notional = final_qty * current_price
    actual_margin = actual_notional / leverage
    resulting_risk = final_qty * hedge_distance

    # Output Results
    print(f"\n--- FIXED-MARGIN POSITION SIZING: {symbol.upper()} ({pos_side.upper()}) ---")
    print(f"Wallet Balance:      {balance:.2f} USDT")
    print(f"Allocation Target:   {margin_percent}% Margin ({target_margin:.2f} USDT)")
    print(f"Leverage:            {leverage}x")
    print(f"--------------------------------")
    print(f"Current Price:       {current_price:.4f}")
    print(f"ATR (15m):           {atr:.4f}")
    print(f"Hedge Distance:      {hedge_distance:.4f} ({hedge_atr_multiplier}x ATR)")
    print(f"--------------------------------")
    print(f"RECOMMENDED QTY:     {final_qty}")
    print(f"NOTIONAL VALUE:      {actual_notional:.2f} USDT")
    print(f"INITIAL MARGIN:      {actual_margin:.2f} USDT ({round((actual_margin/balance)*100, 2)}% of wallet)")
    print(f"--------------------------------")
    print(f"STRATEGY GUIDANCE:")
    print(f"Hedge Trigger:       {hedge_trigger_price:.4f}")
    print(f"RESULTING RISK:      {resulting_risk:.2f} USDT ({round((resulting_risk/balance)*100, 2)}% of wallet)")
    print(f"Hedge Multiplier:    {hedge_atr_multiplier}x ATR")
    print(f"Approx Liquidation:  ~{current_price * (1 - (1/leverage)) if pos_side.upper() == 'LONG' else current_price * (1 + (1/leverage)):.4f}")
    print(f"--------------------------------\n")
    
    return final_qty

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) < 4:
        print("\n--- Fixed-Margin Position Size Calculator ---")
        print("Usage: python calculate_qty.py <symbol> <leverage> <pos_side:LONG|SHORT> [margin_percent] [atr_multiplier]\n")
        print("Arguments:")
        print("  <symbol>         : The symbol to trade (e.g. BTCUSDT)")
        print("  <leverage>       : The leverage to use (Capped at 20x)")
        print("  <pos_side>       : LONG or SHORT")
        print("  [margin_percent] : Optional: Percentage of wallet for initial margin (defaults to 40.0)")
        print("  [atr_multiplier] : Optional: ATR multiplier for Hedge trigger (defaults to 0.5)\n")
        print("Example:")
        print("  python calculate_qty.py BTCUSDT 20 LONG")
        sys.exit(1)
        
    symbol = sys.argv[1]
    leverage = float(sys.argv[2])
    pos_side = sys.argv[3]
    margin_percent = float(sys.argv[4]) if len(sys.argv) > 4 else 40.0
    atr_multiplier = float(sys.argv[5]) if len(sys.argv) > 5 else 0.5
    
    calculate_quantity_fixed_margin(symbol, leverage, pos_side, margin_percent, atr_multiplier)
