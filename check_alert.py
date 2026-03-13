"""
Binance Futures Alert Checker (Automated)

This script provides a centralized system for evaluating trading alerts defined in 'alerts.json'. 
It can be run as a standalone CLI tool or integrated into a real-time monitoring system (e.g., monitor_ws.py).

Key Features:
- Fetches and caches technical indicators (EMA, RSI, ATR, MACD, etc.) using indicators.py.
- Monitors position sizes and real-time mark prices using show_positions.py and get_candles.py.
- Evaluates complex Python-based conditions defined in 'alerts.json' (e.g., 'price > ema25' or 'rsi > 70').
- Executes automated trading actions (opening positions with TP/SL) using place_order.py and protection_order.py.
- Sends system notifications (PowerShell balloon tips) or critical alarms (Blocking MessageBox with sound).
- Handles alert deactivation and linked-alert disabling (mutual exclusion) after successful triggers.

Alert Condition Variables:
    - price: Current mark price (float)
    - pos_amt: Current position size (float, 0 if none)
    - ema7, ema25, ema99: Exponential Moving Averages (float)
    - rsi: Relative Strength Index (float)
    - atr: Average True Range (float)
    - vwap: Volume Weighted Average Price (float)
    - obv: On-Balance Volume (float)
    - macd_hist: MACD Histogram value (float)
    - trend_bias: 'bullish', 'bearish', or 'neutral' based on EMA 25/99 (string)
    - bollinger_upper, bollinger_middle, bollinger_lower: Bollinger Band levels (float)

Usage:
    python check_alert.py [--interval <interval>] [--symbol <symbol>] [--price <price>]

The script reads 'alerts.json' and checks all active alerts. If an interval is provided,
it filters for alerts matching that timeframe. If no interval is provided, it checks
real-time alerts (those with null intervals).
"""

import os
import json
import logging
import argparse
import subprocess
import winsound
import ctypes
import threading
import time
from indicators import get_indicators
from get_candles import get_candles
from show_positions import show_positions
from calculate_qty import calculate_quantity_fixed_margin

# Determine the path to the python executable within the virtual environment
PYTHON_EXE = os.path.join("env", "Scripts", "python.exe")

class DataManager:
    """
    Manages and caches data fetching for indicators, positions, and prices.
    Reduces redundant API calls within a single execution cycle of the script.
    """
    def __init__(self):
        """
        Initializes the data caches for indicators, positions, and candles.
        
        Caches are stored as dictionaries keyed by (symbol, interval) or just symbol.
        """
        self.indicator_cache = {}
        self.position_cache = {}
        self.candle_cache = {}

    def get_indicators(self, symbol, interval):
        """
        Fetches and caches technical indicators for a given symbol and interval.

        Args:
            symbol (str): The trading pair (e.g., 'BTCUSDT').
            interval (str): The timeframe (e.g., '1h', '15m').

        Returns:
            dict: A dictionary containing EMA, RSI, ATR, MACD, VWAP, OBV, and Bollinger values.
                  Returns None if the underlying fetch fails.
        """
        key = (symbol, interval)
        if key not in self.indicator_cache:
            logging.info(f"Fetching indicators for {symbol} ({interval})...")
            self.indicator_cache[key] = get_indicators(symbol, interval)
        return self.indicator_cache[key]

    def get_position(self, symbol):
        """
        Fetches and caches the current position size for a given symbol.
        In Hedge Mode, it returns a dictionary with 'LONG' and 'SHORT' amounts,
        and also a 'NET' amount.

        Args:
            symbol (str): The trading pair (e.g., 'BTCUSDT').

        Returns:
            dict: { 'LONG': float, 'SHORT': float, 'NET': float }. 
                  Returns None if the API call fails.
        """
        if symbol not in self.position_cache:
            positions = show_positions(symbol=symbol)
            if positions is None:
                logging.error(f"Failed to fetch position data for {symbol}.")
                return None
            
            data = {"LONG": 0.0, "SHORT": 0.0, "NET": 0.0}
            for p in positions:
                amt = float(p.get("positionAmt", 0)) if isinstance(p, dict) else float(p.position_amt)
                side = (p.get("positionSide") if isinstance(p, dict) else p.position_side).upper()
                if side in data:
                    data[side] = amt
            
            # NET is the absolute sum of both sides for "active position" check
            data["NET"] = abs(data["LONG"]) + abs(data["SHORT"])
            self.position_cache[symbol] = data
            
        return self.position_cache[symbol]

    def get_price(self, symbol):
        """
        Fetches and caches the current mark price for a given symbol.
        Uses the close price of the most recent 1-minute candle.

        Args:
            symbol (str): The trading pair (e.g., 'BTCUSDT').

        Returns:
            float: The latest price if successful, None otherwise.
        """
        if symbol not in self.candle_cache:
            candles = get_candles(symbol=symbol, interval="1m", limit=1)
            self.candle_cache[symbol] = float(candles[-1][4]) if candles else None
        return self.candle_cache[symbol]

def _show_message_box(title, message, sound_path=None):
    """
    Internal helper to display a Windows MessageBox and optionally play a looping alarm sound.
    This function blocks the thread it runs on until the MessageBox is dismissed.

    Args:
        title (str): Title of the window (appears in the title bar).
        message (str): Message body text (appears in the box content).
        sound_path (str, optional): Absolute path to a .wav file to play in a loop while open.
    """
    if sound_path and os.path.exists(sound_path):
        try:
            # Play sound asynchronously and in a loop
            winsound.PlaySound(sound_path, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_LOOP)
        except Exception as e:
            logging.debug(f"Could not play sound: {e}")
    
    # Display the blocking Win32 MessageBox (type 0: OK button only)
    ctypes.windll.user32.MessageBoxW(0, message, title, 0)
    
    # Stop the sound once the box is closed
    try:
        winsound.PlaySound(None, winsound.SND_PURGE)
    except:
        pass

def notify(title, message, notify_type="notify"):
    """
    Sends a system notification based on the specified level of urgency.

    Args:
        title (str): The notification title (usually the Alert ID).
        message (str): The notification body (usually the Alert Description).
        notify_type (str): 'alarm' for critical alerts (Blocking Win32 MessageBox + Looping Sound),
                           'notify' (or any other) for standard alerts (PS Balloon Tip + Beep).
    """
    logging.info(f"NOTIFICATION ({notify_type}): {title} - {message}")
    if notify_type == "alarm":
        alarm_path = r"C:\Windows\Media\Alarm01.wav"
        # Run MessageBox in a separate thread so it doesn't block the evaluation of other alerts
        thread = threading.Thread(target=_show_message_box, args=(title, message, alarm_path), daemon=False)
        thread.start()
    else:
        # Use PowerShell to show a standard Windows Balloon Tip (non-blocking)
        ps_script = f"""
        [reflection.assembly]::loadwithpartialname('System.Windows.Forms');
        $notification = New-Object System.Windows.Forms.NotifyIcon;
        $notification.Icon = [System.Drawing.SystemIcons]::Information;
        $notification.BalloonTipIcon = 'Info';
        $notification.BalloonTipTitle = '{title}';
        $notification.BalloonTipText = '{message}';
        $notification.Visible = $True;
        $notification.ShowBalloonTip(5000);
        """
        subprocess.run(["powershell", "-Command", ps_script], capture_output=True)
        try:
            winsound.Beep(1000, 500)
        except:
            pass

def run_script(script_name, args):
    """
    Runs a toolkit script as a subprocess using the environment's python executable.

    Args:
        script_name (str): The filename of the Python script (e.g., 'place_order.py').
        args (list): List of command-line arguments to pass to the script.

    Returns:
        subprocess.CompletedProcess: The result object containing stdout, stderr, and returncode.
    """
    cmd = [PYTHON_EXE, script_name] + [str(a) for a in args]
    logging.info(f"Executing: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logging.error(f"Error executing {script_name}: {result.stderr}")
    else:
        logging.info(f"Output from {script_name}: {result.stdout}")
    return result

def execute_action(symbol, action, params, eval_context, alert_id, description=None):
    """
    Executes a complex trading action (e.g., open position) triggered by an alert.
    Handles dynamic quantity calculation and automated TP/SL setup.

    Args:
        symbol (str): The trading pair (e.g., 'BNBUSDT').
        action (str): The action type ('open_long', 'open_short').
        params (dict): Parameters for the action (margin_percent, leverage, use_atr, etc.).
        eval_context (dict): The technical context (price, atr) at the exact time of trigger.
        alert_id (str): The ID of the triggering alert (used for notification title).
        description (str, optional): The description of the alert (used for notification body).
    """
    price = eval_context.get("price")
    atr = eval_context.get("atr")
    
    title = alert_id if alert_id else f"ACTION: {action}"
    message = description if description else f"Condition met for {alert_id}"

    # Notify user that an automated action is being executed
    notify(title, message, notify_type=params.get("notify_type", "notify"))

    if action in ["open_long", "open_short"]:
        pos_side = "LONG" if action == "open_long" else "SHORT"
        side = "BUY" if action == "open_long" else "SELL"

        # Determine quantity: Uses either a fixed 'qty' or calculates it from 'margin_percent'
        qty = params.get("qty")
        if not qty:
            margin_percent = params.get("margin_percent")
            leverage = params.get("leverage", 20)
            if margin_percent:
                qty = calculate_quantity_fixed_margin(symbol, leverage, pos_side, margin_percent)

        if not qty:
            logging.error(f"Could not determine quantity for {action} on {symbol}.")
            return

        # 1. Place the Entry Market Order
        run_script("place_order.py", [symbol, side, "MARKET", qty, pos_side])

        # 2. Set Protection (Stop Loss and Take Profit)
        sl = params.get("sl")
        tp = params.get("tp")

        # If use_atr is true, calculate levels based on current volatility (ATR)
        if params.get("use_atr") and atr:
            mult = params.get("atr_mult", 2.0)
            rr = params.get("rr_ratio", 1.5)
            if pos_side == "LONG":
                sl = price - (mult * atr)
                tp = price + (rr * (price - sl))
            else:
                sl = price + (mult * atr)
                tp = price - (rr * (sl - price))

        if sl:
            prot_side = "SELL" if pos_side == "LONG" else "BUY"
            run_script("protection_order.py", [symbol, prot_side, pos_side, "STOP", sl])
        if tp:
            prot_side = "SELL" if pos_side == "LONG" else "BUY"
            run_script("protection_order.py", [symbol, prot_side, pos_side, "TP", tp])

def load_alerts(filepath="alerts.json", retries=5, delay=0.1):
    """
    Loads alerts from 'alerts.json' with retry logic to handle file locking.
    Useful when multiple processes (like monitor_ws.py) access the file simultaneously.

    Args:
        filepath (str): Path to the alerts JSON file.
        retries (int): Maximum number of retry attempts.
        delay (float): Seconds to wait between retries.

    Returns:
        list: A list of alert dictionaries. Empty list if the file is missing or invalid.
    """
    for i in range(retries):
        try:
            if not os.path.exists(filepath):
                return []
            with open(filepath, "r") as f:
                return json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            if i < retries - 1:
                time.sleep(delay)
                continue
            logging.error(f"Error loading {filepath} after {retries} attempts: {e}")
    return []

def save_alerts(alerts, filepath="alerts.json", retries=5, delay=0.1):
    """
    Persists the updated alerts list back to 'alerts.json' with retry logic.

    Args:
        alerts (list): The complete list of alert dictionaries to save.
        filepath (str): Path to the alerts JSON file.
        retries (int): Maximum number of retry attempts.
        delay (float): Seconds to wait between retries.

    Returns:
        bool: True if the save was successful, False otherwise.
    """
    for i in range(retries):
        try:
            with open(filepath, "w") as f:
                json.dump(alerts, f, indent=4)
            return True
        except IOError as e:
            if i < retries - 1:
                time.sleep(delay)
                continue
            logging.error(f"Error saving {filepath} after {retries} attempts: {e}")
    return False

def evaluate_alerts(target_interval=None, ws_symbol=None, ws_price=None):
    """
    Core engine for alert evaluation.
    
    Workflow:
    1. Loads all active alerts from 'alerts.json'.
    2. Filters based on the target_interval (null for real-time, string for timeframe).
    3. Builds an evaluation context (fetching indicators/positions only if required by conditions).
    4. Executes the condition string using eval().
    5. Triggers actions or notifications on successful evaluation.
    6. Deactivates triggered alerts and any linked 'disables'.
    7. Saves the updated alert states back to the file.

    Args:
        target_interval (str, optional): Filters for alerts with this interval (e.g. '1h').
                                         None targets real-time alerts.
        ws_symbol (str, optional): Hint for the symbol currently being updated (optimization).
        ws_price (float, optional): Hint for the current price (optimization).

    Returns:
        bool: True if any alert was triggered and saved, False otherwise.
    """
    if ws_symbol:
        ws_symbol = ws_symbol.upper()

    alerts = load_alerts()
    if not alerts:
        return False

    # Filter for alerts that are both 'active' and match the requested 'interval' type
    if target_interval:
        active_alerts = [
            a for a in alerts
            if a.get("active", False) and a.get("interval") == target_interval
        ]
    else:
        active_alerts = [
            a for a in alerts
            if a.get("active", False) and a.get("interval") is None
        ]

    if not active_alerts:
        return False

    dm = DataManager()
    alerts_updated = False

    for alert in active_alerts:
        alert_id = alert.get("id")
        symbol = alert.get("symbol").upper()
        condition = alert.get("condition")
        interval = alert.get("interval")
        action = alert.get("action")
        params = alert.get("action_params", {})
        disables = alert.get("disables", [])

        eval_context = {}

        # Scan condition string for keywords to determine which data needs to be fetched
        needs_indicators = any(k in condition for k in ["ema", "rsi", "atr", "vwap", "obv", "macd", "is_squeeze", "trend_bias", "bollinger"])     
        needs_pos = "pos_amt" in condition
        needs_price = "price" in condition

        # Optimization: Use price provided by caller (e.g. WebSocket) if available
        if ws_symbol == symbol and ws_price is not None:
            eval_context["price"] = ws_price

        # Fetch indicator data if the condition requires it
        if needs_indicators and interval:
            base_data = dm.get_indicators(symbol, interval)
            if base_data:
                eval_context.update({
                    "ema7": base_data.get("ema7"),
                    "ema25": base_data.get("ema25"),
                    "ema99": base_data.get("ema99"),
                    "rsi": base_data.get("rsi"),
                    "atr": base_data.get("atr"),
                    "vwap": base_data.get("vwap"),
                    "obv": base_data.get("obv"),
                    "macd_hist": base_data.get("macd")[2] if base_data.get("macd") else None,
                    "bollinger_upper": base_data.get("bb")[0] if base_data.get("bb") else None,
                    "bollinger_middle": base_data.get("bb")[1] if base_data.get("bb") else None,
                    "bollinger_lower": base_data.get("bb")[2] if base_data.get("bb") else None,
                })
                # Derive trend bias from EMAs
                ema25, ema99 = eval_context.get("ema25"), eval_context.get("ema99")
                eval_context["trend_bias"] = "neutral"
                if ema25 and ema99:
                    if ema25 > ema99: eval_context["trend_bias"] = "bullish"
                    elif ema25 < ema99: eval_context["trend_bias"] = "bearish"

                if "price" not in eval_context:
                    eval_context["price"] = base_data.get("price")
        elif needs_indicators and not interval:
            logging.warning(f"Alert {alert_id} requires indicators but has no interval defined. Skipping.")

        # Fetch account position if required
        if needs_pos or "pos_amt_long" in condition or "pos_amt_short" in condition:
            pos_data = dm.get_position(symbol)
            if pos_data:
                eval_context["pos_amt"] = pos_data["NET"]
                eval_context["pos_amt_long"] = pos_data["LONG"]
                eval_context["pos_amt_short"] = pos_data["SHORT"]

        # Fetch price if still missing from context
        if needs_price and "price" not in eval_context:
            precise_price = dm.get_price(symbol)
            if precise_price:
                eval_context["price"] = precise_price

        # Initialize defaults for context variables to prevent eval() from raising NameError
        defaults = {
            "price": 0, "pos_amt": 0, "pos_amt_long": 0, "pos_amt_short": 0,
            "ema7": 0, "ema25": 0, "ema99": 0,
            "rsi": 0, "atr": 0, "macd_hist": 0, "trend_bias": "neutral",
            "bollinger_upper": 0, "bollinger_middle": 0, "bollinger_lower": 0
        }
        for k, v in defaults.items():
            if k not in eval_context: eval_context[k] = v

        logging.info(f"Evaluating {alert_id} ({symbol}): {condition}")
        try:
            # Safely evaluate the user-defined Python expression
            if eval(condition, {"__builtins__": None}, eval_context):
                logging.info(f"ALERT TRIGGERED: {alert_id}")

                description = alert.get("description")
                if action:
                    # Trigger an automated trading action
                    execute_action(symbol, action, params, eval_context, alert_id, description)
                else:
                    # Default: Trigger a simple system notification
                    notify_type = params.get("notify_type", "notify")
                    message = description if description else f"Condition met for {symbol}: {condition}"
                    notify(alert_id, message, notify_type=notify_type)

                # Update the state: Deactivate this alert and all mutual-exclusion alerts
                for a in alerts:
                    if a.get("id") == alert_id:
                        a["active"] = False
                    if a.get("id") in disables:
                        logging.info(f"Deactivating linked alert: {a.get('id')}")
                        a["active"] = False

                alerts_updated = True
        except Exception as e:
            logging.error(f"Error evaluating condition for {alert_id}: {e}")

    # Persist changes to alerts.json if any triggers occurred
    if alerts_updated:
        if save_alerts(alerts):
            logging.info("alerts.json successfully updated.")
            return True
        else:
            logging.error("Failed to update alerts.json.")

    return False

def main():
    """
    Parses command-line arguments and initiates the alert checking cycle.
    """
    parser = argparse.ArgumentParser(
        description="Binance Futures Alert Checker - Evaluates conditions in alerts.json and executes actions.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Available Condition Variables:
  price, pos_amt, ema7, ema25, ema99, rsi, atr, vwap, obv, 
  macd_hist, trend_bias, bollinger_upper, bollinger_middle, bollinger_lower

Examples:
  # Check real-time alerts for all symbols
  python check_alert.py
  
  # Check 1h-timeframe alerts only
  python check_alert.py --interval 1h
  
  # Check alerts for BTCUSDT using a provided price (optimized for WebSockets)
  python check_alert.py --symbol BTCUSDT --price 65000
"""
    )

    parser.add_argument(
        "--interval", 
        help="Filter alerts by timeframe (e.g., '1h', '15m'). If omitted, checks real-time (interval: null) alerts."
    )
    parser.add_argument(
        "--symbol",
        help="Optional: Specify the symbol that triggered the check to optimize data fetching."
    )
    parser.add_argument(
        "--price",
        type=float,
        help="Optional: Provide the current price to skip the API fetch."
    )

    args = parser.parse_args()

    # Run the evaluation engine
    evaluate_alerts(target_interval=args.interval, ws_symbol=args.symbol, ws_price=args.price)

if __name__ == "__main__":
    # Initialize logging configuration only when the script is run directly
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    main()
