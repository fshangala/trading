import sys
import logging
import datetime
from config import get_client

def get_trades(symbol="BNBUSDT", limit=10):
    """
    Fetches the user's recent trade history for a specific symbol on Binance Futures.

    Parameters:
    - symbol (str): The trading pair symbol (e.g., 'BTCUSDT'). Defaults to 'BNBUSDT'.
    - limit (int): The number of recent trades to fetch. Defaults to 10.

    Returns:
    - list: A list of trade data if successful, None otherwise.
    """
    client = get_client()

    try:
        logging.info(f"Fetching last {limit} trades for {symbol}...")
        
        # Fetching historical account trade list
        response = client.rest_api.account_trade_list(symbol=symbol, limit=limit, recv_window=10000)
        trades = response.data()
        
        print(f"\n--- RECENT TRADES: {symbol} ---")
        for trade in trades:
            # Assuming trade is a model or dict
            if isinstance(trade, dict):
                side = "BUY" if trade.get('buyer') else "SELL"
                print(f"ID:           {trade.get('id')}")
                print(f"Order:        {trade.get('orderId')}")
                print(f"Side:         {side}")
                print(f"Price:        {trade.get('price')}")
                print(f"Qty:          {trade.get('qty')}")
                print(f"Commission:   {trade.get('commission')} {trade.get('commissionAsset')}")
                print(f"Realized PnL: {trade.get('realizedPnl')} USDT")
                time_val = trade.get('time')
            else:
                side = "BUY" if trade.buyer else "SELL"
                print(f"ID:           {trade.id}")
                print(f"Order:        {trade.order_id}")
                print(f"Side:         {side}")
                print(f"Price:        {trade.price}")
                print(f"Qty:          {trade.qty}")
                print(f"Commission:   {trade.commission} {trade.commission_asset}")
                print(f"Realized PnL: {trade.realized_pnl} USDT")
                time_val = trade.time
            
            time_str = datetime.datetime.fromtimestamp(time_val/1000).strftime('%Y-%m-%d %H:%M:%S')
            print(f"Time:         {time_str}")
            print(f"------------------------")
        print("")
        
        return trades

    except Exception as e:
        logging.error(f"Failed to fetch trades: {e}")
        return None

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) > 1 and sys.argv[1] in ["-h", "--help"]:
        print("\n--- Binance Futures Account Trade History ---")
        print("Usage: python get_trades.py [symbol] [limit]\n")
        print("Arguments:")
        print("  [symbol] : The symbol to check (default: BNBUSDT)")
        print("  [limit]  : The number of trades to fetch (default: 10)\n")
        print("Example:")
        print("  python get_trades.py BTCUSDT 5")
        sys.exit(0)

    symbol = sys.argv[1] if len(sys.argv) > 1 else "BNBUSDT"
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    get_trades(symbol, limit=limit)
