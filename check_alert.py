"""
Binance Futures Alert Checker (Automated)

This script iterates through active alerts in alerts.json.
- If --interval is provided, it only checks alerts with that specific interval.
- If --interval is NOT provided, it only checks alerts with interval set to null or missing.

Usage:
  python check_alert.py [--interval 1h]
"""

import os
import json
import logging
import sys
import argparse
from indicators import get_indicators
from get_candles import get_candles
from show_positions import show_positions
from calculate_qty import calculate_quantity_margin
import subprocess
import winsound
import ctypes
import threading

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

PYTHON_EXE = os.path.join("env", "Scripts", "python.exe")

class DataManager:
    """
    Manages and caches data fetching for indicators, positions, and prices.
    Reduces redundant API calls within a single execution of the script.
    """
    def __init__(self):
        self.indicator_cache = {}
        self.position_cache = {}
        self.candle_cache = {}

    def get_indicators(self, symbol, interval):
        """Fetches and caches technical indicators for a given symbol and interval."""
        key = (symbol, interval)
        if key not in self.indicator_cache:
            logging.info(f"Fetching indicators for {symbol} ({interval})...")
            self.indicator_cache[key] = get_indicators(symbol, interval)
        return self.indicator_cache[key]

    def get_position(self, symbol):
        """Fetches and caches the current position size for a given symbol."""
        if symbol not in self.position_cache:
            positions = show_positions(symbol=symbol)
            pos_amt = 0
            if positions:
                for p in positions:
                    amt = float(p.get("positionAmt", 0)) if isinstance(p, dict) else float(p.position_amt)
                    if amt != 0:
                        pos_amt = amt
                        break
            self.position_cache[symbol] = pos_amt
        return self.position_cache[symbol]

    def get_price(self, symbol):
        """Fetches and caches the current mark price (1m candle close) for a given symbol."""
        if symbol not in self.candle_cache:
            candles = get_candles(symbol=symbol, interval="1m", limit=1)
            self.candle_cache[symbol] = float(candles[-1][4]) if candles else None
        return self.candle_cache[symbol]

def _show_message_box(title, message, sound_path=None):
    """Internal helper to display a Windows MessageBox and optionally play a sound."""
    if sound_path and os.path.exists(sound_path):
        try:
            winsound.PlaySound(sound_path, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_LOOP)
        except: pass
    ctypes.windll.user32.MessageBoxW(0, message, title, 0)
    try: winsound.PlaySound(None, winsound.SND_PURGE)
    except: pass

def notify(title, message, notify_type="notify"):
    """
    Sends a system notification.
    - 'alarm': Plays a looping sound and shows a blocking MessageBox.
    - 'notify': Shows a non-blocking PowerShell balloon tip and plays a beep.
    """
    logging.info(f"NOTIFICATION ({notify_type}): {title} - {message}")
    if notify_type == "alarm":
        alarm_path = r"C:\Windows\Media\Alarm01.wav"
        thread = threading.Thread(target=_show_message_box, args=(title, message, alarm_path), daemon=False)
        thread.start()
    else:
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
    """Runs a toolkit script as a subprocess and logs output/errors."""
    cmd = [PYTHON_EXE, script_name] + [str(a) for a in args]
    logging.info(f"Executing: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0: logging.error(f"Error: {result.stderr}")
    else: logging.info(f"Output: {result.stdout}")
    return result

def execute_action(symbol, action, params, eval_context):
    """
    Executes a specific trading action (open_long/open_short) based on alert parameters.
    Automatically handles quantity calculation and protection order (TP/SL) placement.
    """
    price = eval_context.get("price")
    atr = eval_context.get("atr")
    
    notify(f"ACTION: {action}", f"Condition met for {symbol}", notify_type=params.get("notify_type", "notify"))

    if action in ["open_long", "open_short"]:
        pos_side = "LONG" if action == "open_long" else "SHORT"
        side = "BUY" if action == "open_long" else "SELL"
        
        qty = params.get("qty")
        if not qty:
            margin_percent = params.get("margin_percent")
            leverage = params.get("leverage", 20)
            if margin_percent:
                qty = calculate_quantity_margin(symbol, margin_percent, leverage, pos_side)
            
        if not qty:
            logging.error("Could not determine quantity.")
            return

        run_script("place_order.py", [symbol, side, "MARKET", qty, pos_side])
        
        sl = params.get("sl")
        tp = params.get("tp")
        
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

import time

def load_alerts(filepath="alerts.json", retries=5, delay=0.1):
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
    Core logic for evaluating alerts. Can be called from CLI or imported as a module.
    """
    if ws_symbol:
        ws_symbol = ws_symbol.upper()
    
    alerts = load_alerts()
    if not alerts:
        return False

    # Filter alerts based on the provided interval
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

        # Build context dynamically
        needs_indicators = any(k in condition for k in ["ema", "rsi", "atr", "vwap", "obv", "macd", "is_squeeze", "trend_bias"])
        needs_pos = "pos_amt" in condition
        needs_price = "price" in condition

        # Priority: If we have a price from the WS for this specific symbol, use it
        if ws_symbol == symbol and ws_price is not None:
            eval_context["price"] = ws_price

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
                })
                ema25, ema99 = eval_context.get("ema25"), eval_context.get("ema99")
                eval_context["trend_bias"] = "neutral"
                if ema25 and ema99:
                    if ema25 > ema99: eval_context["trend_bias"] = "bullish"
                    elif ema25 < ema99: eval_context["trend_bias"] = "bearish"
                
                if "price" not in eval_context: 
                    eval_context["price"] = base_data.get("price")
        elif needs_indicators and not interval:
            logging.warning(f"Alert {alert_id} requires indicators but has no interval defined. Skipping indicator fetch.")

        if needs_pos:
            eval_context["pos_amt"] = dm.get_position(symbol)

        if needs_price and "price" not in eval_context:
            precise_price = dm.get_price(symbol)
            if precise_price:
                eval_context["price"] = precise_price

        # Defaults
        defaults = {"price": 0, "pos_amt": 0, "ema7": 0, "ema25": 0, "ema99": 0, "rsi": 0, "atr": 0, "macd_hist": 0, "trend_bias": "neutral"}
        for k, v in defaults.items():
            if k not in eval_context: eval_context[k] = v

        logging.info(f"Evaluating {alert_id} ({symbol}): {condition}")
        try:
            if eval(condition, {"__builtins__": None}, eval_context):
                logging.info(f"ALERT TRIGGERED: {alert_id}")
                
                if action:
                    execute_action(symbol, action, params, eval_context)
                else:
                    notify("ALERT", f"Condition met for {symbol}: {condition}")

                # Deactivation logic
                for a in alerts:
                    if a.get("id") == alert_id:
                        a["active"] = False
                    if a.get("id") in disables:
                        logging.info(f"Deactivating linked alert: {a.get('id')}")
                        a["active"] = False
                
                alerts_updated = True
        except Exception as e:
            logging.error(f"Error evaluating {alert_id}: {e}")

    if alerts_updated:
        if save_alerts(alerts):
            logging.info("alerts.json updated.")
            return True
        else:
            logging.error("Failed to update alerts.json.")
    
    return False

def main():
    parser = argparse.ArgumentParser(description="Automated alert checker.")
    parser.add_argument("--interval", help="Check only alerts with this interval. If omitted, checks alerts with null/missing interval.")
    parser.add_argument("--symbol", help="The symbol that triggered the alert.")
    parser.add_argument("--price", type=float, help="The current price from the WebSocket.")
    args = parser.parse_args()
    
    evaluate_alerts(target_interval=args.interval, ws_symbol=args.symbol, ws_price=args.price)

if __name__ == "__main__":
    main()
