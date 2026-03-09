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

def calculate_quantity_margin(symbol, margin_percent, leverage, pos_side):
    """
    Calculates the quantity to trade based on a percentage of the available margin and leverage.

    Parameters:
    - symbol (str): The trading pair symbol (e.g., 'BTCUSDT').
    - margin_percent (float): The percentage of the wallet balance to use as margin (0-100).
    - leverage (float): The leverage to apply to the margin.
    - pos_side (str): The position side ('LONG' or 'SHORT').

    Returns:
    - float: The calculated quantity, or None if an error occurs.
    """
    # 1. Get Balance
    balance_data = get_futures_balance("USDT")
    if not balance_data:
        logging.error("Could not fetch USDT balance.")
        return
    
    balance = balance_data["balance"]
    
    # 2. Get Price and ATR (for strategy reference)
    indicators = get_indicators(symbol, "15m")
    if not indicators:
        logging.error("Could not fetch indicators.")
        return
    
    current_price = indicators["price"]
    atr = indicators["atr"]
    
    # 3. Get Symbol Data
    sym_data = get_symbol_data(symbol)
    if not sym_data: return
    precision = sym_data["precision"]
    min_qty = sym_data["min_qty"]
    
    # 4. MARGIN-BASED CALCULATION
    margin_to_use = balance * (margin_percent / 100)
    notional_value = margin_to_use * leverage
    raw_qty = notional_value / current_price
    
    final_qty = round(raw_qty, precision)
    
    if final_qty < min_qty:
        logging.warning(f"Calculated quantity {final_qty} is below minimum {min_qty}.")
        final_qty = min_qty

    # 5. ATR Stop Loss Calculation (For protection_order.py)
    if pos_side.upper() == "LONG":
        stop_loss = current_price - (2 * atr)
    else:
        stop_loss = current_price + (2 * atr)
    sl_distance = abs(current_price - stop_loss)
    
    # 6. Risk Audit
    est_loss = final_qty * sl_distance

    # Output Results
    print(f"\n--- MARGIN-BASED POSITION SIZING: {symbol.upper()} ({pos_side.upper()}) ---")
    print(f"Wallet Balance:      {balance:.2f} USDT")
    print(f"Margin Allocated:    {margin_percent}% ({margin_to_use:.2f} USDT)")
    print(f"Leverage:            {leverage}x")
    print(f"--------------------------------")
    print(f"Current Price:       {current_price:.4f}")
    print(f"--------------------------------")
    print(f"RECOMMENDED QTY:     {final_qty}")
    print(f"NOTIONAL VALUE:      {final_qty * current_price:.2f} USDT")
    print(f"--------------------------------")
    print(f"STRATEGY GUIDANCE (ATR):")
    print(f"ATR (15m):           {atr:.4f}")
    print(f"Recommended SL:      {stop_loss:.4f} (2xATR)")
    print(f"Risk if SL Hit:      {est_loss:.2f} USDT ({round((est_loss/balance)*100, 2)}% of wallet)")
    print(f"Approx Liquidation:  ~{current_price * (1 - (1/leverage)) if pos_side.upper() == 'LONG' else current_price * (1 + (1/leverage)):.4f}")
    print(f"--------------------------------\n")
    
    return final_qty

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) < 5:
        print("\n--- Position Size Calculator ---")
        print("Usage: python calculate_qty.py <symbol> <margin_percent> <leverage> <pos_side:LONG|SHORT>\n")
        print("Arguments:")
        print("  <symbol>         : The symbol to trade (e.g. BTCUSDT)")
        print("  <margin_percent> : Percentage of wallet balance to use (0-100)")
        print("  <leverage>       : The leverage to use (e.g. 20)")
        print("  <pos_side>       : LONG or SHORT\n")
        print("Example:")
        print("  python calculate_qty.py BTCUSDT 20 20 LONG")
        sys.exit(1)
        
    symbol = sys.argv[1]
    margin_percent = float(sys.argv[2])
    leverage = float(sys.argv[3])
    pos_side = sys.argv[4]
    
    calculate_quantity_margin(symbol, margin_percent, leverage, pos_side)
