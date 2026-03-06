# AI Agent Trading Protocol: Multi-Indicator Trend Following

This document provides a standardized protocol for AI agents to execute trades using the Binance Futures Toolkit.

## Phase 1: Market Research
1. **Signal Detection:** Execute `python indicators.py <symbol> <interval>`.
   - **Trend:** Confirm direction with `EMA 7/25/99` and `Bollinger Middle Band`.
   - **Momentum:** Use `RSI` (target < 30 or > 70 for extremes) and `MACD Histogram` (look for crossovers).
   - **Volume:** Check `OBV` and `VWAP` to ensure the move has conviction.
2. **Level Identification:** Use `Bollinger Upper/Lower Bands` and `EMA 99` as primary support and resistance levels.

## Phase 2: Execution
1.  **Entry:** Execute a `MARKET` order using `place_order.py` when 1h and 15m signals align.
2.  **Confirmation:** Immediately run `check_order.py <order_id>` to retrieve the `avgPrice`.

## Phase 3: Risk Management
1.  **Initial Protection:**
    - **Stop Loss (SL):** Use `ATR` for dynamic SL placement (e.g., Entry +/- 1.5 * ATR) or place above/below recent `Bollinger Bands`.
    - **Take Profit (TP):** Target a 1.5:1 Risk/Reward ratio or the next major `EMA 99` level.
2.  **Trailing Stop:** Once a trade is in profit (e.g., > 0.5% gain), convert the fixed SL to a `TRAILING_STOP_MARKET` using `protection_order.py`.
    - *Example:* `python protection_order.py BTCUSDT BUY SHORT TRAILING 0.5 None 0.002`

## Phase 4: Automated Monitoring
1.  **Alerts:** Configure `alerts.json` for breakout levels or RSI extremes.
    - Use the `disables` feature to manage mutually exclusive trade setups.
2.  **Execution:** Run `monitor.py` in the background to handle rule-based exits or entries.
3.  **Audit:** Use `get_fees.py` after closure to audit net results, accounting for taker fees (0.04%).

## Safety Constraints
- **Hedge Mode:** Always specify `LONG` or `SHORT` for `pos_side`.
- **Pre-fetching:** Use `monitor.py --once` to verify market state before committing to a full loop.
- **Testnet:** Ensure `base_path` in scripts points to `demo-fapi.binance.com`.
