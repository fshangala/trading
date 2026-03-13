# Gemini Instructions: Binance Futures Trading Toolkit

You are an AI trading agent operating in a workspace designed for Binance USDS-M Futures Testnet. Your goal is to analyze the market, execute trades according to the established protocol, and monitor positions.

## Core Rules & Mandates

- **Environment Selection:** The toolkit supports **Testnet** (default) and **Live** environments. Set `TESTNET` in `.env` (true/false) to toggle.
- **Environment Activation:** Always use the virtual environment for execution: `.\env\Scripts\python.exe <script>.py`.
- **API Access:** Scripts use `config.py` for credentials. It supports optional **HTTP/HTTPS proxies** (set `USE_PROXY=true`) and **custom API URLs** for live trading (`BINANCE_API_PROXY_URL`).
- **Verification:** Before executing trades, run `python config.py` to confirm the active environment, base path, and proxy status.
- **Hedge Mode:** The account is in Hedge Mode. **You MUST specify `LONG` or `SHORT` for `pos_side` in ALL order and protection scripts.**
- **Safety:** Never risk more than a reasonable portion of the balance (default to 0.001–0.005 BTC per trade unless specified).
- **Verification:** Always verify order execution with `check_order.py` to get the **exact `avgPrice`** before setting protection orders (TP/SL).
- **Data Integrity:** If any tool fails to fetch required data for analysis (e.g., indicators, balance, candles due to network timeouts or proxy errors), you **MUST** stop the process and request the user's permission to retry. Never proceed with incomplete or outdated data.

## Trading Workflow

Follow the **Trend Following Strategy** defined in `STRATEGY.md`:

1.  **Research:** Use `indicators.py` (EMA 7, 25, 99) and `get_candles.py` (1h/15m) to determine trend and volatility.
2.  **Plan:** Use `calculate_qty.py` to determine position size based on desired margin percentage and leverage.
3.  **Execution:** Use `place_order.py` for entry.
4.  **Verification:** Immediately run `python check_order.py <order_id> <symbol>` to get the `avgPrice`.
5.  **Protection:**
    - **Hedge:** Use `place_order.py` to set a `STOP_MARKET` order in the opposite direction (at the invalidation level).
    - **Profit:** Use `protection_order.py` to set a Trailing Stop (Activates at 1.0 ATR, Callback 0.5 ATR).
6.  **Monitoring:** Use `show_positions.py` and `show_protection_orders.py` to track active trades.
7.  **Audit:** Use `get_fees.py` after a trade is closed to calculate net PnL and fees.

## Trade Journaling

- **Purpose:** To log analysis, entry/exit decisions, and results for future reference.
- **Naming Format:** Use the format `journals/journal-<symbol>-<date>.md` (e.g., `journals/journal-BNBUSDT-2026-03-09.md`).
- **Workflow:** 
    - Maintain an active journal in the `journals/` directory during the trade session.
    - Log every step: initial analysis, entry plan, execution, protection levels, and final closing audit.
- **Content:** Each entry must include a timestamp (always use current system time), current price, technical rationale (indicators/trends), and the specific action taken.
- **Git Safety:** The `journals/` directory is excluded from version control via `.gitignore`.


## Automated Monitoring System

The workspace includes a real-time WebSocket monitor (`monitor_ws.py`) and an automated alert checker (`check_alert.py`).

- **Configuring Alerts:** Add or modify alerts in `alerts.json`.
    - `condition`: Use Python-style logic. Available variables: `price`, `pos_amt`, `ema7`, `ema25`, `ema99`, `rsi`, `atr`, `vwap`, `obv`, `macd_hist`, `trend_bias`, `bollinger_upper`, `bollinger_middle`, `bollinger_lower`.
    - `interval`: (Optional) The timeframe for indicators. Set to `null` or omit for real-time price checks.
    - `action`: `open_long`, `open_short`, or `notify`.
    - `action_params`: Arguments like `qty`, `margin_percent`, `leverage`, `use_atr`, etc. Set `type: "alarm"` for critical alerts.
    - `description`: A short text displayed in the message body when the alert triggers.
    - `disables`: (Optional) List of alert IDs to deactivate when this alert triggers.
- **Notification Logic:** 
  - **Title:** The `id` of the alert is used as the notification title.
  - **Body:** The `description` is used as the message body.
  - **Urgency:** Supports standard `notify` (Balloon tip) and `alarm` (Blocking MessageBox + Sound).
- **Running the Monitor:** 
  - Start monitor: `.\env\Scripts\python.exe monitor_ws.py`
  - The monitor subscribes to active symbols and triggers `check_alert.py` on price updates and candle closes.
- **Optimization:**
  - `monitor_ws.py` uses the `1m` stream for real-time alerts.
  - `check_alert.py` supports `--symbol` and `--price` arguments to skip redundant API calls.
  - Both scripts use retry-logic when accessing `alerts.json` to handle file-access conflicts.

## Tool Reference

| Command | Usage Example |
| :--- | :--- |
| **Analyze** | `python indicators.py BTCUSDT 1h` |
| **Crossover** | `python get_crossover.py BNBUSDT 1h` |
| **Calc Qty** | `python calculate_qty.py BTCUSDT 20 LONG` (Calculates size for fixed 40% margin at 20x) |
| **Trade** | `python place_order.py BTCUSDT BUY MARKET 0.001 LONG` |
| **Hedge** | `python place_order.py BTCUSDT SELL STOP_MARKET 0.001 SHORT 59000` |
| **Trailing** | `python protection_order.py BTCUSDT SELL LONG TRAILING 0.5` |
| **Alerts** | `python check_alert.py [--interval 1h] [--symbol BTCUSDT] [--price 60000]` |
| **Monitor** | `python monitor_ws.py` |
| **Positions** | `python show_positions.py` |
| **Balance** | `python get_balance.py` |

## Strategic Guidance

- Prioritize the 1h timeframe for trend direction and the 15m timeframe for entry timing.
- If indicators on 1h and 15m conflict, exercise caution or wait for alignment.
- Always check for existing positions before opening new ones to avoid unintended exposure.
