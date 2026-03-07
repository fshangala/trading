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

| Script | Description | Primary Usage |
| :--- | :--- | :--- |
| `get_candles.py` | Fetches OHLCV data. | `python get_candles.py <symbol> <interval> <limit>` |
| `indicators.py` | Calculates EMA 7, 25, 99 and VWAP. | `python indicators.py <symbol> <interval>` |
| `place_order.py` | Executes Market/Limit orders. | `python place_order.py <symbol> <side> <type> <qty> <pos_side> [price]` |
| `protection_order.py` | Sets TP, SL, and Trailing stops. | `python protection_order.py <symbol> <side> <pos_side> <type:STOP\|TP\|TRAILING> <price/callback> [working_type/activation] [qty]` |
| `cancel_protection.py` | Cancels a specific algo order. | `python cancel_protection.py <symbol> <algo_id>` |
| `show_protection_orders.py` | Displays open TP/SL orders. | `python show_protection_orders.py [symbol]` |
| `show_positions.py` | Displays active positions. | `python show_positions.py [symbol]` |
| `show_orders.py` | Lists recent order history. | `python show_orders.py [symbol]` |
| `check_order.py` | Detailed status of one order. | `python check_order.py <order_id> [symbol]` |
| `get_balance.py` | Fetches available futures balance. | `python get_balance.py [asset]` |
| `get_crossover.py` | Finds the last EMA 25/99 crossover. | `python get_crossover.py <symbol> <interval>` |
| `get_fees.py` | Calculates PnL and Fees. | `python get_fees.py <entry> <exit> <qty> [symbol]` |

## Typical Workflow
1. **Analyze:** Run `indicators.py` and `get_candles.py` to determine trend and volatility.
2. **Execute:** Use `place_order.py` to enter a position.
3. **Verify:** Use `check_order.py` to get the exact `avgPrice`.
4. **Protect:** Use `protection_order.py` to set TP and SL based on entry.
5. **Monitor:** Use `show_positions.py` to track unrealized PnL.
6. **Analyze Costs:** Use `get_fees.py` after closing to audit net profit.

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
1. **Pre-fetches Data:** Efficiently fetches indicators, positions, and candles (in that order) for all active symbols upfront.
2. **Evaluates Conditions:** Uses the cached market state to check if the `condition` in `alerts.json` is met.
3. **Triggers Actions:** 
   - **Automatic Notification:** Every triggered alert sends a notification. Action-specific alerts provide descriptive messages (e.g., "Opening LONG").
   - `open_long` / `open_short`: Automatically executes trade and protection logic.
   - `adjust_sl`: Prompts the user to adjust their stop loss.
4. **Auto-Deactivation:** Once an alert is triggered, its `active` status is set to `false`. Any IDs listed in `disables` are also deactivated.
