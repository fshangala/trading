# Multi-Indicator Trend Following Strategy

This strategy combines multiple technical indicators to confirm trend direction, momentum, and volatility-based risk management on the Binance USDS-M Futures market.

## 1. Indicator Hierarchy
To avoid analysis paralysis, indicators are prioritized by their role:

### Tier 1: Primary (Trend & Bias)
- **EMA 25 & 99:** Defines the "Line in the Sand" (Price above/below for bias).
- **RSI (14):** Acts as a "Gatekeeper" (Avoid buying if >70, avoid selling if <30).

### Tier 2: Secondary (Entry Triggers)
- **EMA 7:** Used for short-term momentum and precise entry timing.
- **MACD (12, 26, 9):** Histogram confirms if momentum is accelerating or slowing down.

### Tier 3: Risk & Structure
- **ATR (14):** Strictly for setting Stop Loss (SL) and Take Profit (TP) distances based on volatility.
- **Bollinger Bands (20, 2):** Identifies "The Squeeze" (low volatility phases) to avoid entries or anticipate breakouts.

### Tier 4: Confirmation & Planning (Optional)
- **OBV (On-Balance Volume):** Confirms if volume supports the price movement.
- **Daily VWAP:** Identifies institutional "fair value" levels. Price significantly far from Daily VWAP suggests the asset is overextended (high probability of mean reversion).

## 2. Market Analysis Protocol
Before every trade, analyze the 1h (Primary) and 15m (Entry) timeframes.

### Step 1: Trend Confirmation & Age Analysis
- **Bullish Bias:** Price > EMA 25 > EMA 99.
- **Bearish Bias:** Price < EMA 25 < EMA 99.
- **Mandatory Filter (Squeeze Check):** The **Bollinger Band Width** must be expanding or at a minimum "healthy" width.
  - **The Squeeze:** If BB bands are exceptionally tight/flat, **DO NOT ENTER.** This is a consolidation phase where EMAs are prone to whipsaws.
  - **Wait for Breakout:** Only enter when price breaks out of the BB squeeze with increasing volume (OBV) and widening bands.
- **Trend Age (Crucial):** Identify the most recent **EMA 25/99 Cross** (Golden/Death Cross).
  - **Early Trend:** Cross happened within the last 5-15 candles (High probability entry).
  - **Mature Trend:** Cross happened 30+ candles ago (Higher risk of reversal; avoid chasing).
  - **Tool:** `python get_crossover.py <symbol> 1h`.

### Step 2: Entry Setup (Pullback Protocol)
Instead of entering immediately on a cross (which often "leads" to buying the top), wait for a pullback:
- **LONG Entry:** Price pulls back to touch or hover near the **EMA 25** while EMA 25 > EMA 99.
- **SHORT Entry:** Price rallies back to touch or hover near the **EMA 25** while EMA 25 < EMA 99.
- **Validation:** RSI should be in the **40-60 range** (neutral) during the pullback, ensuring the trend isn't already exhausted.

### Step 3: Momentum & Volatility Check (Tier 2/3)
- **MACD Histogram:** Ensure the histogram matches the bias direction during the pullback recovery.
- **Bollinger Bands:** Avoid entries if the pullback is so deep it touches the opposite band (possible trend reversal). Ideally, the pullback stays within the Middle Band (SMA 20).

### Step 3: Volume Confirmation
- **OBV:** Should be trending in the same direction as the price.
- **VWAP:** Price above VWAP supports longs; price below VWAP supports shorts.

## 3. Execution Rules

### Position Sizing (Margin-Based Model)
To maintain consistent capital allocation, calculate the quantity based on the percentage of your wallet you wish to commit as margin:
- **Margin Allocation:** **10-20%** of total wallet balance per trade.
- **Leverage:** Use **10x to 20x** depending on volatility.
- **Tool:** `python calculate_qty.py <symbol> <margin_percent> <leverage> <pos_side:LONG|SHORT>`.
- **Goal:** Control exactly how much capital (margin) is tied up in each trade.

### Entry (SHORT Example)
1. **Trend:** 1h Death Cross confirmed. 15m EMA 7 < 25.
2. **Setup:** Price rallies to the 15m EMA 25 or Middle Bollinger Band.
3. **Trigger:** Bearish rejection (RSI starts falling from 50-60 level, MACD histogram shrinks).
4. **Execution:** Run `calculate_qty.py` to get recommended quantity, then `python place_order.py <symbol> SELL MARKET <qty> SHORT`.

### Risk Management (ATR-Based)
- **Stop Loss (SL):** Place SL at `Entry + (2 * ATR)` for shorts, or `Entry - (2 * ATR)` for longs. Use the ATR from the entry timeframe (e.g., 15m).
- **Take Profit (TP):** Aim for a minimum **1.5:1** Risk/Reward ratio relative to the SL distance.
  - *Example:* If SL distance is 100 points, TP should be at 150 points from entry.
- **Trailing Stop (Volatility-Based):** 
  - **Activation:** Once the price reaches a profit of **1.5 * ATR (15m)**.
  - **Callback Rate:** Set the trailing callback to **1.0 * ATR (15m)** expressed as a percentage of the current price, or a minimum of **1%** to avoid premature exit from minor noise.
  - **Logic:** This ensures the "breathing room" for the trade scales with the asset's current volatility.
- **Tool:** `python protection_order.py <symbol> <side> <pos_side> TRAILING <callback_percentage>`.

## 4. Monitoring & Audit
- Use `monitor.py` with `alerts.json` to automate TP/SL and breakout notifications.
- Use `get_fees.py` after every trade to audit net PnL (including maker/taker commissions).
