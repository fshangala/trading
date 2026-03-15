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
| `get_trades.py` | Fetches historical account trade list (includes exact commissions). | `python get_trades.py [symbol] [limit]` |
| `get_fees.py` | Estimates commissions and net PnL for a trade (predictive). | `python get_fees.py <entry> <exit> <qty> [symbol]` |

## Audit vs. Estimation
- **Post-Trade Audit:** Always use `get_trades.py` to fetch the **exact `commission`** and `realizedPnl` from the exchange ledger. This is the ground truth for your journal.
- **Pre-Trade Planning:** Use `get_fees.py` to estimate the potential transaction costs based on your current account's Maker/Taker rates.

## Typical Workflow
1. **Analyze:** Run `indicators.py` and `get_candles.py` to determine trend and volatility.
2. **Plan:** Use `calculate_qty.py` to determine the position size.
3. **Execute:** Use `place_order.py` to enter a position.
4. **Verify:** Use `check_order.py` to get the exact `avgPrice`.
5. **Protect:** Use `protection_order.py` to set TP and SL based on the verified entry price.
| `check_alert.py` | Automated alert checker for all active alerts. | `python check_alert.py [--interval <val>] [--symbol <sym>] [--price <prc>]` |
| `monitor_ws.py` | Real-time WebSocket monitor and alert trigger. | `python monitor_ws.py` |

## Automated Monitoring

The toolkit includes a real-time WebSocket monitoring system (`monitor_ws.py`) and a condition-evaluation engine (`check_alert.py`).

### Configuration (`alerts.json`)
The `alerts.json` file contains a list of alert objects. Each object can contain the following fields:

| Field | Type | Description |
| :--- | :--- | :--- |
| `id` | `string` | **Mandatory.** A unique identifier for the alert. Used as the title in system notifications. |
| `symbol` | `string` | **Mandatory.** The trading pair (e.g., `BTCUSDT`). |
| `active` | `boolean` | **Mandatory.** Set to `true` to enable the alert, `false` to ignore it. |
| `condition` | `string` | **Mandatory.** A Python-evaluable expression. Supports boolean operators (`and`, `or`, `not`) and parentheses. (e.g., `price > ema25 and rsi < 70`). |
| `interval` | `string` | The timeframe for technical indicators (e.g., `1m`, `5m`, `15m`, `1h`, `4h`, `1d`). Set to `null` or omit for real-time price-only alerts. |
| `description` | `string` | The text message shown in the notification body. |
| `action` | `string` | The automated task to perform when triggered. Options: `notify` (default), `open_long`, `open_short`. |
| `action_params` | `object` | Parameters for the action. Common fields: `notify_type` (`notify` or `alarm`). For `open_*` actions: `qty`, `margin_percent`, `leverage`, `sl`, `tp`, `use_atr`, `atr_mult`, `rr_ratio`. |
| `disables` | `array` | A list of other alert IDs (strings) to automatically deactivate when this alert triggers (used for mutual exclusion). |

#### Available Condition Variables:
- **Price:** `price` (Current Mark Price).
- **Position:** `pos_amt` (Net absolute exposure), `pos_amt_long`, `pos_amt_short`.
- **Indicators:** `ema7`, `ema25`, `ema99`, `rsi`, `atr`, `vwap`, `obv`, `macd_hist`.
- **Bollinger:** `bollinger_upper`, `bollinger_middle`, `bollinger_lower`.
- **Trend:** `trend_bias` (`"bullish"`, `"bearish"`, or `"neutral"`).

### Optimization & Reliability
- **WebSocket Efficiency:** `monitor_ws.py` uses per-stream `on_message` subscriptions to minimize overhead.
- **Delta-Based Subscriptions:** When `alerts.json` changes, the monitor only subscribes/unsubscribes to the difference, avoiding unnecessary connection churn.
- **Per-Symbol Throttling:** Throttling timers are maintained independently for each symbol to prevent cross-interference in multi-symbol monitoring.
- **Position State Tracking:** Maintains a state machine (`NONE`, `LONG`, `SHORT`, `HEDGE`) for active symbols. 
    - **Proactive Triggers:** Transitions (e.g., `LONG -> NONE`) trigger an **immediate** alert evaluation.
    - **Hedge Safety:** Upon `HEDGE` detection, the monitor automatically cancels all open orders for the symbol.
- **Health & Recovery:** A background `connection_health_check` monitors for silence/timeouts and triggers a graceful shutdown and notify on failure.

### Execution
1. **WebSocket Monitor:** Run `python monitor_ws.py` in the background. It subscribes to streams for all active alerts.
   - Triggers `check_alert.py` (no interval) from the `1m` stream for real-time responsiveness.
   - Triggers `check_alert.py --interval <val>` only when a candle closes for the specified timeframe.
2. **Alert Checker:** `check_alert.py` reads `alerts.json`, evaluates conditions using local context (passed price) or fetched indicators, and executes actions. It automatically deactivates triggered alerts.

