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

## Trading Workflow

Follow the **Trend Following Strategy** defined in `STRATEGY.md`:

1.  **Research:** Use `indicators.py` (EMA 7, 25, 99) and `get_candles.py` (1h/15m) to determine trend and volatility.
2.  **Plan:** Use `calculate_qty.py` to determine position size based on desired margin percentage and leverage.
3.  **Execution:** Use `place_order.py` for entry.
4.  **Verification:** Immediately run `python check_order.py <order_id> <symbol>` to get the `avgPrice`.
5.  **Protection:** Use `protection_order.py` to set TP and SL levels based on ATR (2x for SL, 1.5:1 RR for TP) using the verified `avgPrice`.
6.  **Monitoring:** Use `show_positions.py` and `show_protection_orders.py` to track active trades.
7.  **Audit:** Use `get_fees.py` after a trade is closed to calculate net PnL and fees.

## Trade Journaling

- **Purpose:** To log analysis, entry/exit decisions, and results for future reference.
- **Naming Format:** Use the format `journal-<symbol>-<date>.md` (e.g., `journal-BNBUSDT-2026-03-09.md`).
- **Workflow:** 
    - Maintain an active journal during the trade session.
    - Log every step: initial analysis, entry plan, execution, protection levels, and final closing audit.
- **Content:** Each entry must include a timestamp, current price, technical rationale (indicators/trends), and the specific action taken.
- **Git Safety:** All files matching `journal-*.md` are excluded from version control via `.gitignore`.


## Automated Monitoring System

The workspace includes a background monitor (`monitor.py`) that uses `alerts.json` for rule-based actions.

- **Configuring Alerts:** You can add or modify alerts in `alerts.json`.
    - `condition`: Use Python-style logic (e.g., `price < 70000`, `pos_amt == 0`).
    - `action`: `open_long`, `open_short`, or `adjust_sl`. If omitted, defaults to a notification.
    - `action_params`: Pass arguments like `qty`, `tp`, or `sl`.
    - **Example Alert:** `{"id": "btc_breakout", "symbol": "BTCUSDT", "condition": "price > 75000", "action": "open_long", "action_params": {"qty": 0.001}, "active": true}`
    - **Note:** The monitor reloads `alerts.json` every loop iteration (default 1 minute).
- **Running the Monitor:** 
  - Start loop: `.\env\Scripts\python.exe monitor.py`
  - Test once: `.\env\Scripts\python.exe monitor.py --once`
- **Management:** Triggered alerts are automatically set to `active: false`. Re-enable them if needed.

## Tool Reference

| Command | Usage Example |
| :--- | :--- |
| **Analyze** | `python indicators.py BTCUSDT 1h` |
| **Crossover** | `python get_crossover.py BNBUSDT 1h` |
| **Calc Qty** | `python calculate_qty.py BTCUSDT 20 20 LONG` |
| **Trade** | `python place_order.py BTCUSDT BUY MARKET 0.001 LONG` |
| **Cancel** | `python cancel_order.py BTCUSDT 94480020406` |
| **Protect** | `python protection_order.py BTCUSDT SELL LONG TRAILING 0.5` |
| **Positions** | `python show_positions.py` |
| **Balance** | `python get_balance.py` |
| **Orders** | `python show_orders.py BTCUSDT` |

## Strategic Guidance

- Prioritize the 1h timeframe for trend direction and the 15m timeframe for entry timing.
- If indicators on 1h and 15m conflict, exercise caution or wait for alignment.
- Always check for existing positions before opening new ones to avoid unintended exposure.
