import sys
import logging
import datetime
from config import get_client

def get_trades(symbol="BNBUSDT", limit=10):
    client = get_client()

    try:
        logging.info(f"Fetching last {limit} trades for {symbol}...")
        # Most binance SDKs have account_trade_list or user_trades
        # Trying user_trades based on common SDK patterns
        response = client.rest_api.account_trade_list(symbol=symbol, limit=limit)
        trades = response.data()
        
        print(f"\n--- RECENT TRADES: {symbol} ---")
        for trade in trades:
            # Assuming trade is a model or dict
            if isinstance(trade, dict):
                side = "BUY" if trade.get('buyer') else "SELL"
                print(f"ID:      {trade.get('id')}")
                print(f"Order:   {trade.get('orderId')}")
                print(f"Side:    {side}")
                print(f"Price:   {trade.get('price')}")
                print(f"Qty:     {trade.get('qty')}")
                print(f"Realized PnL: {trade.get('realizedPnl')} USDT")
                time_val = trade.get('time')
            else:
                side = "BUY" if trade.buyer else "SELL"
                print(f"ID:      {trade.id}")
                print(f"Order:   {trade.order_id}")
                print(f"Side:    {side}")
                print(f"Price:   {trade.price}")
                print(f"Qty:     {trade.qty}")
                print(f"Realized PnL: {trade.realized_pnl} USDT")
                time_val = trade.time
            
            time_str = datetime.datetime.fromtimestamp(time_val/1000).strftime('%Y-%m-%d %H:%M:%S')
            print(f"Time:    {time_str}")
            print(f"------------------------")
        print("")
        
        return trades

    except Exception as e:
        logging.error(f"Failed to fetch trades: {e}")
        # Try to list available methods if it fails
        logging.info(f"Available methods in rest_api: {[m for m in dir(client.rest_api) if not m.startswith('_')]}")
        return None

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    symbol = sys.argv[1] if len(sys.argv) > 1 else "BNBUSDT"
    get_trades(symbol)
