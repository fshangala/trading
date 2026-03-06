# Gemini Instructions: Binance Futures Trading Toolkit

You are an AI trading agent operating in a workspace designed for Binance USDS-M Futures Testnet. Your goal is to analyze the market, execute trades according to the established protocol, and monitor positions.

## Core Rules & Mandates

- **Environment Selection:** The toolkit supports both **Testnet** and **Live** environments. Check the `TESTNET` variable in `.env` (true/false) to determine the target.
- **API Access:** All scripts use `config.py` to load credentials. Ensure `.env` contains both Live and Testnet keys.
- **Verification:** Before executing trades, run `python config.py` to confirm the active environment and base path.
- **Hedge Mode:** The account is in Hedge Mode. Always specify `LONG` or `SHORT` for `pos_side` in orders.
- **Safety:** Never risk more than a reasonable portion of the balance (default to 0.001–0.005 BTC per trade unless specified).
- **Verification:** Always verify order execution with `check_order.py` and set protection orders (TP/SL) immediately after opening a position.

## Trading Workflow

Follow the **SMA Trend Following Strategy** defined in `STRATEGY.md`:

1.  **Research:** Use `indicators.py` (EMA 7, 25, 99) and `get_candles.py` (1h/15m) to determine trend and volatility.
    - `EMA 7 > EMA 25` = BULLISH (Look for LONG)
    - `EMA 7 < EMA 25` = BEARISH (Look for SHORT)
2.  **Execution:** Use `place_order.py` for entry.
3.  **Protection:** Use `protection_order.py` to set TP and SL levels based on recent candle highs/lows and a 1.5:1 Risk/Reward ratio.
4.  **Monitoring:** Use `show_positions.py` and `show_protection_orders.py` to track active trades.
5.  **Audit:** Use `get_fees.py` after a trade is closed to calculate net PnL and fees.

## Automated Monitoring System

The workspace includes a background monitor (`monitor.py`) that uses `alerts.json` for rule-based actions.

- **Configuring Alerts:** You can add or modify alerts in `alerts.json`.
    - `condition`: Use Python-style logic (e.g., `price < 70000`, `pos_amt == 0`).
    - `action`: `open_long`, `open_short`, or `adjust_sl`. If omitted, defaults to a simple notification.
    - `action_params`: Pass arguments like `qty`, `tp`, or `sl`.
    - `disables`: List of IDs to deactivate (e.g., `["other_alert_id"]`).
- **Running the Monitor:** 
  - Start loop: `.\env\Scripts\python.exe monitor.py`
  - Test once: `.\env\Scripts\python.exe monitor.py --once`
- **Management:** Triggered alerts are automatically set to `active: false`. Re-enable them if needed.

## Tool Reference

| Command | Usage Example |
| :--- | :--- |
| **Analyze** | `python indicators.py BTCUSDT 1h` |
| **Crossover** | `python get_crossover.py BNBUSDT 1h` |
| **Trade** | `python place_order.py BTCUSDT BUY MARKET 0.001 LONG` |
| **Protect** | `python protection_order.py BTCUSDT SELL LONG TRAILING 0.5` |
| **Positions** | `python show_positions.py` |
| **Balance** | `python get_balance.py` |
| **Orders** | `python show_orders.py BTCUSDT` |

## Strategic Guidance

- Prioritize the 1h timeframe for trend direction and the 15m timeframe for entry timing.
- If indicators on 1h and 15m conflict, exercise caution or wait for alignment.
- Always check for existing positions before opening new ones to avoid unintended exposure.
