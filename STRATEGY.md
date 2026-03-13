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
Operate across a hierarchical timeframe model to align macro bias with precision execution.

### Tier 1: Macro Bias (1h)
- **Role:** Trend Direction & Major Support/Resistance.
- **Goal:** Identify the "Line in the Sand" (EMA 25/99).
- **Mandate:** Only trade in the direction of the 1h EMA 25 bias (Long if Price > EMA 25).

### Tier 2: Structural Integrity (15m)
- **Role:** Identifying pullbacks and breakouts within the macro trend.
- **Goal:** Monitor Bollinger Band status and EMA 99 (Intraday Trend).
- **Mandate:** Look for price holding or reclaiming the 15m EMA 99 or Middle Bollinger Band.

### Tier 3: Momentum & Entry Trigger (3m)
- **Role:** Confirming trend shifts and momentum acceleration.
- **Goal:** EMA 7/25 crossovers (Golden/Death Cross).
- **Mandate:** Use 3m momentum shifts to signal the start of a "recollection" or "flush."

### Tier 4: Precision Execution (1m)
- **Role:** Timing the entry/exit to maximize risk/reward.
- **Goal:** RSI cool-off (target 50-60 range) and candle close confirmations.
- **Mandate:** Avoid "chasing" overbought moves (RSI > 80); wait for the 1m pullback.

### Step 1: Trend Confirmation & Age Analysis
- **Bullish Bias:** Price > EMA 25 > EMA 99.
- **Bearish Bias:** Price < EMA 25 < EMA 99.
- **Mandatory Filter (Bollinger Squeeze & Breakout Protocol):**
  - **The Squeeze (Consolidation):** If all EMAs (7, 25, 99) are clustered near the Middle Bollinger Band and the bands are shrinking/tightening, **DO NOT ENTER.** This is a high-risk consolidation phase.
  - **The Breakout (Confirmation):** A new trend is only confirmed when a candle **closes outside** the Upper or Lower Bollinger Band with expanding bandwidth.
  - **Action:** Monitor the 15m/3m bands for this breakout before initiating any "Trend Following" or "Value Entry" positions.
- **Trend Age (Crucial):** Identify the most recent **EMA 25/99 Cross** (Golden/Death Cross).
  - **Early Trend (1-15 Candles):** High probability entry. Breakout/Momentum entries permitted.
  - **Mid Trend (15-30 Candles):** Medium risk. ONLY enter on pullbacks to the **15m EMA 25**.
  - **Mature Trend (>30 Candles):** High risk. ONLY enter on deep pullbacks to the **1h EMA 25** or **Daily VWAP**, or skip the trade entirely.
  - **Exhaustion Filter (New):**
    - **MACD Divergence:** If Price makes a Higher High but MACD Histogram makes a Lower High (Bearish Divergence) on 1h/15m, **DO NOT ENTER**.
    - **RSI Overextension:** If RSI > 70 on 1h, wait for reset < 60 before considering long entries.
  - **Tool:** `python get_crossover.py <symbol> 1h`.

### Step 2: Entry Setup (Value Entry Protocol)
Instead of entering immediately on a cross (which often "leads" to buying the top), wait for a "Value Entry":
- **Trigger:** Price pulls back to the **15m EMA 25** or **1h EMA 25**.
- **Validation:** RSI should be in the **40-50 range (for longs)** or **50-60 range (for shorts)** during the pullback.
- **Momentum:** Enter on the **first** bullish/bearish 3m candle close (early signal) instead of waiting for full MACD acceleration.

### Step 3: Market Correlation & Funding Check
- **BTC Rule:** For ANY trade, **BTCUSDT** must not be in a direct momentum conflict. (e.g., Don't long BNB if BTC is breaking down through its 1h EMA 25).
- **Funding Check:** Avoid opening new positions if the **Funding Rate** is extreme (e.g., >0.03% for longs) to avoid "liquidation flushes."

## 3. Execution Rules

### Position Sizing (Margin-Based Model)
To protect capital while maintaining aggressive exposure, position sizing is based on **Fixed Margin Allocation**.
- **Initial Margin:** Always use **40%** of Total Wallet Balance for the primary position.
- **Formula:** `Quantity = (Wallet Balance * 0.40 * Leverage) / Current Price`
- **Safety Caps (Mandatory):**
  - **Max Leverage:** Strictly **20x**.
  - **Total Margin Cap:** Primary (40%) + Hedge (40%) = **80%** total margin usage when locked.
- **Logic:** This model allocates a significant portion of the wallet to the trade immediately. The "Risk if Hedge is Hit" (Quantity * 0.5 ATR) is dynamic and must be noted upon entry. This model assumes the user is confident in the setup and prepared for the management required in a "Locked" state.
- **Tool:** `python calculate_qty.py <symbol> <leverage> <pos_side:LONG|SHORT> [margin_percent:40.0]`.

### Entry (SHORT Example)
1. **Trend:** 1h Death Cross confirmed (< 30 candles old). 15m EMA 7 < 25.
2. **Setup:** Price rallies to the 15m EMA 25 or Middle Bollinger Band.
3. **Trigger:** Bearish rejection (RSI starts falling from 50-60 level).
4. **Execution:** Run `calculate_qty.py` to get risk-based quantity, then `python place_order.py <symbol> SELL MARKET <qty> SHORT`.

### Risk Management (Hedge Protection)
- **Hedge Order (The "Delta-Neutral" Stop):** Instead of closing the position, place a **STOP_MARKET** entry order in the opposite direction using the `protection_order.py` script. This opens a "Hedge" position, locking in the loss and moving the account to a net-zero (delta-neutral) state.
  - **Trigger:** Set at **Entry +/- 0.5 * ATR**. (Tight hedge to limit initial drawdown).
  - **Quantity:** Equal to the initial position size (`1:1 Hedge`).
  - **Critical Parameter:** You **MUST** set `close_position="false"` and specify the **opposite `position_side`** (e.g., if Primary is LONG, Hedge is SHORT).
  - **Mutual Cancellation (OCO):**
    - If the **Trailing Stop** (Profit) triggers first, **CANCEL** the Hedge Order.
    - If the **Hedge Order** (Loss) triggers first, **CANCEL** the Trailing Stop (to prevent naked exposure).
  - **Tool:** `python protection_order.py <symbol> <OPPOSITE_SIDE> <OPPOSITE_POS_SIDE> STOP <trigger_price> CONTRACT_PRICE <qty> false`

- **Hard Take Profit (TP):** Set at **2.0 * ATR** from entry.

- **Trailing Stop (Scalping Mode):**
  - **Activation:** Once the price reaches a profit of **1.0 * ATR** (approx 0.5% move).
  - **Callback Rate:** **0.5 * ATR** (Tight trailing to lock in scalp profits).
  - **Logic:** Secure profits early in volatile markets. If the trend is strong, this captures the "meat" of the move without risking a full reversal.
- **Tool:** `python protection_order.py <symbol> <side> <pos_side> TRAILING <callback_percentage>`.

### Hedge Unwind Protocol (Recovery)
When the Hedge is active (Locked Position) and price tests a major support/resistance and holds (rebound):
1.  **Close Hedge:** Market Close the **Winning Leg** (e.g., Short) to realize the profit.
2.  **Protect Primary:** Immediately set a **Stop Loss** on the **Primary Leg** (e.g., Long) at the **Price where the Hedge was closed**.
    - *Purpose:* Prevents the loss from exceeding the "Locked" amount if the rebound fails.
3.  **Trail Primary:** Set a **Trailing Stop** on the Primary Leg with **Activation: 0.5 * ATR** (from current price) and **Callback: 0.5 * ATR**.
4.  **Cleanup:** Monitor the Trailing Stop. Once the Trailing Stop's trigger price moves past the fixed Stop Loss (better exit), **CANCEL** the fixed Stop Loss to let the Trailing Stop manage the trade.


## 4. Monitoring & Audit
- Use `monitor.py` with `alerts.json` to automate TP/SL and breakout notifications.
- Use `get_fees.py` after every trade to audit net PnL (including maker/taker commissions).
- **Mandatory Trade Journaling:** 
    - Maintain a journal for every trade in `journals/`.
    - **Do not just log stats.** Provide a narrative description of what is happening in the market based on the indicators (e.g., "The price is pulling back to the 15m EMA 25 while macro trend is bullish").
    - **Explicit Decisions:** Clearly state what has been decided based on the analysis (e.g., "Waiting for a 3m Golden Cross before entry").
