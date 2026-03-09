# Binance Futures Trading Toolkit

A modular Python toolkit for interacting with the Binance USDS-M Futures Testnet. This toolkit is designed for manual CLI use or automation via AI agents.

## Prerequisites
- **Python 3.10+**
- **Virtual Environment:** Must be activated (`.\env\Scripts\Activate.ps1`).
- **Configuration:** `.env` file containing `BINANCE_API_KEY` and `BINANCE_API_SECRET`.

## Configuration

The toolkit supports both **Testnet** and **Live** environments via a centralized `config.py`.

### Environment Setup (`.env`)
Manage your keys, environment selection, and optional proxy settings in the `.env` file:
```ini
# Set to 'true' for Testnet, 'false' for Live (defaults to true)
TESTNET=false

# Live Credentials
BINANCE_API_KEY=your_live_key
BINANCE_API_SECRET=your_live_secret
# Optional: Custom API Base URL for Live (e.g., for a proxy or local gateway)
BINANCE_API_PROXY_URL=https://fapi.binance.com/

# Testnet Credentials
BINANCE_TESTNET_API_KEY=your_testnet_key
BINANCE_TESTNET_API_SECRET=your_testnet_secret

# Optional: Global Proxy Settings
USE_PROXY=false
BINANCE_API_PROXY_HOST=127.0.0.1
BINANCE_API_PROXY_PORT=8080
BINANCE_API_PROXY_PROTOCOL=http
BINANCE_API_PROXY_USERNAME=optional_user
BINANCE_API_PROXY_PASSWORD=optional_pass
```
All scripts automatically load these settings using `config.py`.

## Script Reference

All scripts support `-h` or `--help` for detailed usage instructions.

| Script | Description | Primary Usage |
| :--- | :--- | :--- |
| `get_candles.py` | Fetches OHLCV data. | `python get_candles.py <symbol> <interval> <limit>` |
| `indicators.py` | Calculates EMA, MACD, RSI, Bollinger, ATR, VWAP, OBV. | `python indicators.py <symbol> <interval>` |
| `calculate_qty.py` | Calculates quantity based on margin % and leverage. | `python calculate_qty.py <symbol> <margin_percent> <leverage> <pos_side>` |
| `place_order.py` | Executes Market, Limit, or Trailing Stop orders. | `python place_order.py <symbol> <side> <type> <qty> <pos_side> [price/callback] [activation]` |
| `cancel_order.py` | Cancels a specific order. | `python cancel_order.py <symbol> <order_id>` |
| `protection_order.py` | Sets TP, SL, and Trailing stops (Algo orders). | `python protection_order.py <symbol> <side> <pos_side> <type> [trigger/callback] [working/activate] [qty] [close_position]` |
| `cancel_protection.py` | Cancels a specific algo order. | `python cancel_protection.py <symbol> <algo_id>` |
| `show_protection_orders.py` | Displays open TP/SL/Trailing orders. | `python show_protection_orders.py [symbol]` |
| `show_positions.py` | Displays active positions and unrealized PnL. | `python show_positions.py [symbol]` |
| `show_orders.py` | Lists recent order history (filled/cancelled). | `python show_orders.py [symbol] [limit]` |
| `check_order.py` | Detailed status and average fill price of an order. | `python check_order.py <order_id> [symbol]` |
| `get_balance.py` | Fetches available futures balance (USDT/BNB/etc). | `python get_balance.py [asset]` |
| `get_crossover.py` | Finds the last EMA 25/99 Golden/Death Cross. | `python get_crossover.py <symbol> <interval> [limit]` |
| `get_trades.py` | Fetches historical account trade list. | `python get_trades.py [symbol] [limit]` |
| `get_fees.py` | Calculates commissions and net PnL for a trade. | `python get_fees.py <entry> <exit> <qty> [symbol]` |
| `monitor.py` | Background market and alert monitoring system. | `python monitor.py [--once]` |

## Typical Workflow
1. **Analyze:** Run `indicators.py` and `get_candles.py` to determine trend and volatility.
2. **Plan:** Use `calculate_qty.py` to determine the position size.
3. **Execute:** Use `place_order.py` to enter a position.
4. **Verify:** Use `check_order.py` to get the exact `avgPrice`.
5. **Protect:** Use `protection_order.py` to set TP and SL based on the verified entry price.
6. **Monitor:** Use `show_positions.py` and `show_protection_orders.py` to track active trades.
7. **Analyze Costs:** Use `get_fees.py` after closing to audit net profit and commissions.

## Automated Monitoring

The toolkit includes a background monitoring system consisting of `monitor.py` and `alerts.json`. This system allows for rule-based alerts and automated trade actions.

### Configuration (`alerts.json`)
The `alerts.json` file contains a list of alert objects. Each object can include:
- `id`: Unique identifier for the alert.
- `symbol`: The trading pair (e.g., `BTCUSDT`).
- `condition`: A Python-evaluable string (e.g., `price < 60000` or `pos_amt == 0`).
- `action`: The action to take when the condition is met (`open_long`, `open_short`, `adjust_sl`, or omit for default notification).
- `action_params`: (Optional) A dictionary of parameters for the action.
- `disables`: (Optional) A list of alert IDs to deactivate when this alert is triggered.
- `active`: A boolean to enable or disable the alert.

### Execution (`monitor.py`)
Run the monitor in a background terminal:
```powershell
.\env\Scripts\python.exe monitor.py
```
**How it works:**
1. **Reloads Alerts:** The monitor reloads `alerts.json` at every loop iteration (default 1 minute).
2. **Pre-fetches Data:** Efficiently fetches indicators, positions, and prices for all active symbols upfront.
3. **Evaluates Conditions:** Uses the cached market state to check if the `condition` in `alerts.json` is met.
4. **Triggers Actions:** 
   - **Automatic Notification:** Every triggered alert sends a notification.
   - `open_long` / `open_short`: Automatically executes trade logic.
5. **Auto-Deactivation:** Once an alert is triggered, its `active` status is set to `false`.
