# Binance Futures Trading Toolkit

A modular Python toolkit for interacting with the Binance USDS-M Futures Testnet. This toolkit is designed for manual CLI use or automation via AI agents.

## Prerequisites
- **Python 3.10+**
- **Virtual Environment:** Must be activated (`.\env\Scripts\Activate.ps1`).
- **Configuration:** `.env` file containing `BINANCE_API_KEY` and `BINANCE_API_SECRET`.

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
- `action`: The action to take when the condition is met (`notify`, `open_long`, `adjust_sl`).
- `action_params`: (Optional) A dictionary of parameters for the action (e.g., `{"qty": 0.001, "tp": 70000}`).
- `active`: A boolean to enable or disable the alert.

### Execution (`monitor.py`)
Run the monitor in a background terminal:
```powershell
.\env\Scripts\python.exe monitor.py
```
**How it works:**
1. **Polls Data:** Every 60 seconds, it fetches the latest price, indicators, and position status for active alerts.
2. **Evaluates Conditions:** It uses the current market state to check if the `condition` in `alerts.json` is met.
3. **Triggers Actions:** 
   - `notify`: Triggers a Windows system beep and a message box.
   - `open_long`: Automatically executes `place_order.py` and `protection_order.py`.
   - `adjust_sl`: Prompts the user to adjust their stop loss.
4. **Auto-Deactivation:** Once an alert is triggered, its `active` status is set to `false` in `alerts.json` to prevent repeated execution.
