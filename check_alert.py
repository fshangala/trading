"""
Binance Futures Alert Checker (Automated)

This script provides a centralized system for evaluating trading alerts defined in 'alerts.json'. 
It can be run as a standalone CLI tool or integrated into a real-time monitoring system (e.g., monitor_ws.py).

Key Features:
- Fetches and caches technical indicators (EMA, RSI, ATR, MACD, etc.).
- Monitors position sizes and real-time mark prices.
- Evaluates complex Python-based conditions defined in alerts.
- Executes automated trading actions (opening positions with TP/SL).
- Sends system notifications (PowerShell balloon tips) or critical alarms (Blocking MessageBox with sound).
- Handles alert deactivation and linked-alert disabling (mutual exclusion).

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
        """Initializes the data caches for indicators, positions, and candles."""
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
            dict: Indicator data dictionary if successful, None otherwise.
        """
        key = (symbol, interval)
        if key not in self.indicator_cache:
            logging.info(f"Fetching indicators for {symbol} ({interval})...")
            self.indicator_cache[key] = get_indicators(symbol, interval)
        return self.indicator_cache[key]

    def get_position(self, symbol):
        """
        Fetches and caches the current position size for a given symbol.
        
        Args:
            symbol (str): The trading pair.
            
        Returns:
            float: The absolute position amount (quantity). Returns 0 if no position.
        """
        if symbol not in self.position_cache:
            positions = show_positions(symbol=symbol)
            pos_amt = 0
            if positions:
                for p in positions:
                    # Handle both dictionary and object-like response structures
                    amt = float(p.get("positionAmt", 0)) if isinstance(p, dict) else float(p.position_amt)
                    if amt != 0:
                        pos_amt = amt
                        break
            self.position_cache[symbol] = pos_amt
        return self.position_cache[symbol]

    def get_price(self, symbol):
        """
        Fetches and caches the current mark price (latest 1m candle close) for a given symbol.
        
        Args:
            symbol (str): The trading pair.
            
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
        title (str): Title of the window.
        message (str): Message body text.
        sound_path (str, optional): Path to a .wav file to play in a loop while open.
    """
    if sound_path and os.path.exists(sound_path):
        try:
            # Play sound asynchronously and in a loop
            winsound.PlaySound(sound_path, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_LOOP)
        except: pass
    
    # Display the blocking Win32 MessageBox
    ctypes.windll.user32.MessageBoxW(0, message, title, 0)
    
    # Stop the sound once the box is closed
    try: winsound.PlaySound(None, winsound.SND_PURGE)
    except: pass

def notify(title, message, notify_type="notify"):
    """
    Sends a system notification based on the specified level of urgency.
    
    Args:
        title (str): The notification title (usually the Alert ID).
        message (str): The notification body (usually the Alert Description).
        notify_type (str): 'alarm' for critical alerts (MessageBox + Sound), 
                           'notify' for standard alerts (Balloon Tip + Beep).
    """
    logging.info(f"NOTIFICATION ({notify_type}): {title} - {message}")
    if notify_type == "alarm":
        alarm_path = r"C:\Windows\Media\Alarm01.wav"
        # Run MessageBox in a separate thread so it doesn't block the entire script execution
        thread = threading.Thread(target=_show_message_box, args=(title, message, alarm_path), daemon=False)
        thread.start()
    else:
        # Use PowerShell to show a standard Windows Balloon Tip
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
        try: winsound.Beep(1000, 500)
        except: pass

def run_script(script_name, args):
    """
    Runs a toolkit script as a subprocess and logs its output or errors.
    
    Args:
        script_name (str): The filename of the Python script (e.g., 'place_order.py').
        args (list): List of command-line arguments for the script.
        
    Returns:
        subprocess.CompletedProcess: The result object of the script execution.
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
    Executes a complex trading action (open_long/open_short) triggered by an alert.
    Handles quantity calculation (Fixed-Margin model) and sets up TP/SL protection orders.
    
    Args:
        symbol (str): The trading pair.
        action (str): The action type ('open_long', 'open_short', etc.).
        params (dict): Parameters for the action (margin_percent, leverage, use_atr, etc.).
        eval_context (dict): The technical context (price, atr) at the time of trigger.
        alert_id (str): The ID of the triggering alert (used for notification title).
        description (str, optional): The description of the alert (used for notification body).
    """
    price = eval_context.get("price")
    atr = eval_context.get("atr")
    
    title = alert_id if alert_id else f"ACTION: {action}"
    message = description if description else f"Condition met for {alert_id}"

    # Send initial notification about the action being taken
    notify(title, message, notify_type=params.get("notify_type", "notify"))

    if action in ["open_long", "open_short"]:
        pos_side = "LONG" if action == "open_long" else "SHORT"
        side = "BUY" if action == "open_long" else "SELL"

        # Determine quantity: Fixed qty OR calculated based on margin %
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

        # 2. Set Protection (TP/SL)
        sl = params.get("sl")
        tp = params.get("tp")

        # If use_atr is true, calculate levels based on volatility
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
    Loads alerts from a JSON file with retry logic to handle file-access conflicts.
    
    Args:
        filepath (str): Path to the alerts JSON file.
        retries (int): Number of retries on failure (useful for concurrent access).
        delay (float): Delay between retries in seconds.
        
    Returns:
        list: List of alert dictionaries. Returns empty list if file not found or corrupted.
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
    Saves the list of alerts to a JSON file with retry logic.
    
    Args:
        alerts (list): The list of alert dictionaries to save.
        filepath (str): Path to the alerts JSON file.
        retries (int): Number of retries on failure.
        delay (float): Delay between retries in seconds.
        
    Returns:
        bool: True if save was successful, False otherwise.
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
    Core engine for alert evaluation. Parses alerts.json, builds execution context,
    evaluates Python conditions, and triggers actions/notifications.
    
    Args:
        target_interval (str, optional): If provided, only check alerts matching this interval.
                                         If None, checks alerts with no interval (real-time).
        ws_symbol (str, optional): Symbol provided by a WebSocket event for optimization.
        ws_price (float, optional): Price provided by a WebSocket event to avoid redundant API calls.
        
    Returns:
        bool: True if any alert was triggered and the file was updated, False otherwise.
    """
    if ws_symbol:
        ws_symbol = ws_symbol.upper()

    alerts = load_alerts()
    if not alerts:
        return False

    # Filter alerts based on the provided interval and 'active' status
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

        # Build context dynamically based on what the condition string requires
        needs_indicators = any(k in condition for k in ["ema", "rsi", "atr", "vwap", "obv", "macd", "is_squeeze", "trend_bias", "bollinger"])    
        needs_pos = "pos_amt" in condition
        needs_price = "price" in condition

        # Priority: If we have a price from the WS for this specific symbol, use it
        if ws_symbol == symbol and ws_price is not None:
            eval_context["price"] = ws_price

        # Fetch indicators if needed and an interval is defined
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
                ema25, ema99 = eval_context.get("ema25"), eval_context.get("ema99")
                eval_context["trend_bias"] = "neutral"
                if ema25 and ema99:
                    if ema25 > ema99: eval_context["trend_bias"] = "bullish"
                    elif ema25 < ema99: eval_context["trend_bias"] = "bearish"

                if "price" not in eval_context:
                    eval_context["price"] = base_data.get("price")
        elif needs_indicators and not interval:
            logging.warning(f"Alert {alert_id} requires indicators but has no interval defined. Skipping.")

        # Fetch position if needed
        if needs_pos:
            eval_context["pos_amt"] = dm.get_position(symbol)

        # Fetch price if still needed
        if needs_price and "price" not in eval_context:
            precise_price = dm.get_price(symbol)
            if precise_price:
                eval_context["price"] = precise_price

        # Default values for the evaluation context to avoid KeyErrors during eval()
        defaults = {
            "price": 0, "pos_amt": 0, "ema7": 0, "ema25": 0, "ema99": 0, 
            "rsi": 0, "atr": 0, "macd_hist": 0, "trend_bias": "neutral",
            "bollinger_upper": 0, "bollinger_middle": 0, "bollinger_lower": 0
        }
        for k, v in defaults.items():
            if k not in eval_context: eval_context[k] = v

        logging.info(f"Evaluating {alert_id} ({symbol}): {condition}")
        try:
            # Safely evaluate the condition string within the provided context
            if eval(condition, {"__builtins__": None}, eval_context):
                logging.info(f"ALERT TRIGGERED: {alert_id}")

                description = alert.get("description")
                if action:
                    # Execute complex action (e.g. open trade)
                    execute_action(symbol, action, params, eval_context, alert_id, description)
                else:
                    # Simple notification only
                    notify_type = params.get("type", "notify")
                    message = description if description else f"Condition met for {symbol}: {condition}"
                    notify(alert_id, message, notify_type=notify_type)

                # Deactivation logic: Deactivate this alert and any linked alerts
                for a in alerts:
                    if a.get("id") == alert_id:
                        a["active"] = False
                    if a.get("id") in disables:
                        logging.info(f"Deactivating linked alert: {a.get('id')}")
                        a["active"] = False

                alerts_updated = True
        except Exception as e:
            logging.error(f"Error evaluating condition for {alert_id}: {e}")

    # Save changes if any alerts were triggered
    if alerts_updated:
        if save_alerts(alerts):
            logging.info("alerts.json successfully updated.")
            return True
        else:
            logging.error("Failed to update alerts.json.")

    return False

def main():
    """
    Main entry point for CLI execution. Parses command-line arguments and triggers alert evaluation.
    Includes custom help text for all arguments.
    """
    parser = argparse.ArgumentParser(
        description="Binance Futures Alert Checker - Evaluates conditions in alerts.json and executes actions.",
        epilog="Examples:\n  python check_alert.py --interval 1h\n  python check_alert.py --symbol BTCUSDT --price 65000",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--interval", 
        help="The timeframe to filter alerts by (e.g., '1h', '15m', '3m'). If omitted, checks 'real-time' alerts (interval=null)."
    )
    parser.add_argument(
        "--symbol", 
        help="The symbol that triggered the event (used to optimize context fetching)."
    )
    parser.add_argument(
        "--price", 
        type=float, 
        help="The current price (usually passed from WebSocket) to avoid redundant API calls."
    )
    
    args = parser.parse_args()

    # Trigger the evaluation process
    evaluate_alerts(target_interval=args.interval, ws_symbol=args.symbol, ws_price=args.price)

if __name__ == "__main__":
    # Configure logging to output to console with timestamps
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    main()
