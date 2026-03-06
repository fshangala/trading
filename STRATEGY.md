# AI Agent Trading Protocol: SMA Trend Following

This document provides a standardized protocol for AI agents to execute trades using the Binance Futures Toolkit.

## Phase 1: Market Research
1. **Signal Detection:** Execute `python indicators.py <symbol> <interval>`. 
   - If `EMA 7 > EMA 25`: Market is in an uptrend.
   - If `EMA 7 < EMA 25`: Market is in a downtrend.
2. **Level Identification:** Execute `python get_candles.py BTCUSDT 1h 10`.
   - Identify the `High` and `Low` of the current and previous candles.
   - These levels serve as natural support/resistance for TP and SL placement.

## Phase 2: Execution
1. **Entry:** Use `place_order.py` to execute a `MARKET` order in the direction of the signal.
   - *Example (Short):* `python place_order.py BTCUSDT SELL MARKET 0.002 SHORT`
2. **Confirmation:** Immediately run `check_order.py <order_id>` to retrieve the `avgPrice`.

## Phase 3: Risk Management
1. **Stop Loss (SL):** 
   - For `SHORT`: Place SL ~0.1% - 0.5% above the recent candle high.
   - For `LONG`: Place SL ~0.1% - 0.5% below the recent candle low.
2. **Take Profit (TP):**
   - Aim for a Risk/Reward ratio of at least 1.5:1.
   - Place TP at the next major psychological level or support/resistance zone.
3. **Set Orders:** Use `protection_order.py` for both SL and TP.

## Phase 4: Monitoring & Closure
1. **Tracking:** Use `show_positions.py` every 5-15 minutes to monitor unrealized PnL.
2. **Manual Exit:** If the market sentiment changes or a target is reached manually, use `place_order.py` to close the position and then audit the net result with `get_fees.py`.

## Safety Constraints
- **Hedge Mode:** Always specify `LONG` or `SHORT` for `position_side`.
- **Close All:** Always ensure protection orders use `close_position=True` (handled by the script) to avoid accidental over-leveraging.
- **Testnet:** Ensure `base_path` in scripts points to `demo-fapi.binance.com`.
