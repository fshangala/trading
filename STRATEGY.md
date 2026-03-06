# Multi-Indicator Trend Following Strategy

This strategy combines multiple technical indicators to confirm trend direction, momentum, and volatility-based risk management on the Binance USDS-M Futures market.

## 1. Core Indicators
- **Trend:** EMA 7, 25, 99.
- **Momentum:** MACD (12, 26, 9) and RSI (14).
- **Volatility:** Bollinger Bands (20, 2) and ATR (14).
- **Volume:** OBV (On-Balance Volume) and VWAP.

## 2. Market Analysis Protocol
Before every trade, analyze the 1h (Primary) and 15m (Entry) timeframes.

### Step 1: Trend Confirmation
- **Bullish:** `EMA 7 > EMA 25 > EMA 99`. Look for a recent **Golden Cross** (EMA 25 crosses above EMA 99).
- **Bearish:** `EMA 7 < EMA 25 < EMA 99`. Look for a recent **Death Cross** (EMA 25 crosses below EMA 99).
- **Tool:** `python get_crossover.py <symbol> 1h`.

### Step 2: Momentum & Volatility Check
- **MACD:** Ensure the histogram matches the trend (Positive for LONG, Negative for SHORT).
- **RSI:** Avoid entries when `RSI > 70` (Overbought) for longs or `RSI < 30` (Oversold) for shorts.
- **Bollinger Bands:** Look for entries near the Middle Band (SMA 20) after a pull-back. Avoid "chasing" the price if it's already outside the Upper or Lower bands.

### Step 3: Volume Confirmation
- **OBV:** Should be trending in the same direction as the price.
- **VWAP:** Price above VWAP supports longs; price below VWAP supports shorts.

## 3. Execution Rules

### Entry (SHORT Example)
1. **Trend:** 1h Death Cross confirmed. 15m EMA 7 < 25.
2. **Setup:** Price rallies to the 15m EMA 25 or Middle Bollinger Band.
3. **Trigger:** Bearish rejection (RSI starts falling from 50-60 level, MACD histogram shrinks).
4. **Tool:** `python place_order.py <symbol> SELL MARKET <qty> SHORT`.

### Risk Management (ATR-Based)
- **Stop Loss (SL):** Place SL at `Entry + (2 * ATR)` for shorts, or `Entry - (2 * ATR)` for longs.
- **Take Profit (TP):** Aim for a minimum **1.5:1** Risk/Reward ratio.
- **Trailing Stop:** Once the price reaches **0.5% profit**, convert the fixed SL into a **0.5% Trailing Stop**.
- **Tool:** `python protection_order.py <symbol> <side> <pos_side> <type> <price/callback>`.

## 4. Monitoring & Audit
- Use `monitor.py` with `alerts.json` to automate TP/SL and breakout notifications.
- Use `get_fees.py` after every trade to audit net PnL (including maker/taker commissions).
