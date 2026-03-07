import os
import json
import time
import logging
import winsound
import ctypes
import subprocess
import threading
from indicators import get_indicators
from get_candles import get_candles
from show_positions import show_positions
from calculate_qty import calculate_quantity_margin

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("monitor.log"),
        logging.StreamHandler()
    ]
)

PYTHON_EXE = os.path.join("env", "Scripts", "python.exe")

class DataManager:
    def __init__(self):
        self.indicator_cache = {} # (symbol, interval) -> data
        self.position_cache = {}  # symbol -> pos_amt
        self.candle_cache = {}    # symbol -> price

    def get_indicators(self, symbol, interval):
        key = (symbol, interval)
        if key not in self.indicator_cache:
            logging.info(f"Fetching indicators for {symbol} ({interval})")
            self.indicator_cache[key] = get_indicators(symbol, interval)
        return self.indicator_cache[key]

    def get_position(self, symbol):
        if symbol not in self.position_cache:
            logging.info(f"Fetching position for {symbol}")
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
        if symbol not in self.candle_cache:
            logging.info(f"Fetching latest price for {symbol}")
            candles = get_candles(symbol=symbol, interval="1m", limit=1)
            self.candle_cache[symbol] = float(candles[-1][4]) if candles else None
        return self.candle_cache[symbol]

def _show_message_box(title, message, sound_path=None):
    # If sound path is provided, start the looping sound in this thread
    if sound_path and os.path.exists(sound_path):
        try:
            winsound.PlaySound(sound_path, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_LOOP)
        except Exception as e:
            logging.error(f"Failed to play sound: {e}")
            winsound.Beep(1000, 1000)
    
    # This blocks THIS background thread until dismissed
    ctypes.windll.user32.MessageBoxW(0, message, title, 0)
    
    # Stop the sound after dismiss
    try:
        winsound.PlaySound(None, winsound.SND_PURGE)
    except:
        pass

def _system_notification(title, message):
    # PowerShell Balloon Tip (Transient)
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

def notify(title, message, notify_type="notify"):
    logging.info(f"NOTIFICATION ({notify_type}): {title} - {message}")
    
    if notify_type == "alarm":
        # Launch persistent background thread for Alarm
        alarm_path = r"C:\Windows\Media\Alarm01.wav"
        # daemon=False ensures the thread lives even if the main loop iteration ends
        thread = threading.Thread(target=_show_message_box, args=(title, message, alarm_path), daemon=False)
        thread.start()
    else:
        # Transient System Tray Notification
        _system_notification(title, message)
        # Short beep for attention
        try: winsound.Beep(1000, 500)
        except: pass

def run_script(script_name, args):
    cmd = [PYTHON_EXE, script_name] + [str(a) for a in args]
    logging.info(f"Executing automation: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0: logging.error(f"Script error: {result.stderr}")
    else: logging.info(f"Script output: {result.stdout}")
    return result

def execute_action(alert, eval_context):
    action = alert.get("action")
    params = alert.get("action_params", {})
    symbol = alert["symbol"]
    alert_id = alert["id"]
    notify_type = alert.get("notify_type", "notify") # Default to transient notification
    price = eval_context.get("price")
    atr = eval_context.get("atr")

    # Determine message based on action
    if action == "adjust_sl":
        msg = f"Action required: Adjust SL for {symbol} to {params['new_sl']}"
    elif action in ["open_long", "open_short"]:
        pos_side = "LONG" if action == "open_long" else "SHORT"
        msg = f"Opening {pos_side} for {symbol} (Condition Met)"
    else:
        msg = f"Condition met for {symbol}"

    # ALWAYS Notify if notify_type is provided
    if notify_type:
        notify(f"ACTION: {alert_id}" if action else f"ALERT: {alert_id}", msg, notify_type=notify_type)

    # Execute specific action logic
    if action == "adjust_sl":
        logging.info(f"Execution: Adjust SL for {symbol}")

    elif action in ["open_long", "open_short"]:
        pos_side = "LONG" if action == "open_long" else "SHORT"
        side = "BUY" if action == "open_long" else "SELL"
        
        # Determine Quantity
        qty = params.get("qty")
        if not qty:
            margin_percent = params.get("margin_percent")
            leverage = params.get("leverage", 20)
            if margin_percent:
                logging.info(f"Calculating dynamic qty for {symbol} using {margin_percent}% margin and {leverage}x leverage")
                qty = calculate_quantity_margin(symbol, margin_percent, leverage, pos_side)
            
        if not qty:
            logging.error(f"Could not determine quantity for {alert_id}. Skipping action.")
            return

        logging.info(f"Execution: Opening {pos_side} for {symbol} with qty {qty}")
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
            logging.info(f"Calculated ATR-based SL: {sl:.4f}, TP: {tp:.4f} (ATR: {atr:.4f}, Price: {price:.4f})")

        if sl:
            prot_side = "SELL" if pos_side == "LONG" else "BUY"
            run_script("protection_order.py", [symbol, prot_side, pos_side, "STOP", sl])
        if tp:
            prot_side = "SELL" if pos_side == "LONG" else "BUY"
            run_script("protection_order.py", [symbol, prot_side, pos_side, "TP", tp])
    else:
        # Default action is already handled by the notification above
        pass

def check_alerts():
    if not os.path.exists("alerts.json"): return

    try:
        with open("alerts.json", "r") as f:
            alerts = json.load(f)
    except Exception as e:
        logging.error(f"Error reading alerts.json: {e}")
        return

    active_alerts = [a for a in alerts if a.get("active", False)]
    if not active_alerts: return

    # Initialize Lazy Data Manager for this iteration
    dm = DataManager()
    alerts_updated = False

    for alert in active_alerts:
        symbol = alert["symbol"]
        interval = alert.get("interval", "1h")
        condition = alert["condition"]
        
        needs_indicators = any(k in condition for k in ["ema", "rsi", "atr", "vwap", "obv", "macd", "is_squeeze", "trend_bias"])
        needs_pos = "pos_amt" in condition
        needs_price = "price" in condition

        eval_context = {}

        if needs_indicators:
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
                bb = base_data.get("bb")
                if bb and all(v is not None for v in bb):
                    width = bb[0] - bb[2]
                    eval_context["bb_width_pct"] = (width / bb[1]) * 100
                    eval_context["is_squeeze"] = eval_context["bb_width_pct"] < 1.5
                else:
                    eval_context["is_squeeze"] = False
                
                ema25, ema99 = eval_context.get("ema25"), eval_context.get("ema99")
                eval_context["trend_bias"] = "neutral"
                if ema25 and ema99:
                    if ema25 > ema99: eval_context["trend_bias"] = "bullish"
                    elif ema25 < ema99: eval_context["trend_bias"] = "bearish"
                
                if needs_price and "price" not in eval_context:
                    eval_context["price"] = base_data.get("price")

        if needs_pos:
            eval_context["pos_amt"] = dm.get_position(symbol)

        if needs_price:
            precise_price = dm.get_price(symbol)
            if precise_price:
                eval_context["price"] = precise_price

        defaults = {"price": 0, "pos_amt": 0, "ema7": None, "ema25": None, "ema99": None, "rsi": None, "atr": 0, "is_squeeze": False, "trend_bias": "neutral"}
        for k, v in defaults.items():
            if k not in eval_context: eval_context[k] = v

        logging.info(f"Evaluating {alert['id']} (Condition: {condition})")
        
        try:
            if eval(condition, {"__builtins__": None}, eval_context):
                logging.info(f"Condition MET for {alert['id']}!")
                execute_action(alert, eval_context)
                alert["active"] = False
                disables = alert.get("disables", [])
                if disables:
                    for other_id in disables:
                        for a in alerts:
                            if a["id"] == other_id and a["active"]: a["active"] = False
                alerts_updated = True
        except Exception as e:
            logging.error(f"Error evaluating alert {alert['id']}: {e}")

    if alerts_updated:
        with open("alerts.json", "w") as f:
            json.dump(alerts, f, indent=4)

def main():
    import sys
    run_once = "--once" in sys.argv
    logging.info(f"Monitor Active (Once: {run_once})")
    while True:
        try:
            check_alerts()
            if run_once: break
            time.sleep(60)
        except KeyboardInterrupt: break
        except Exception as e:
            logging.error(f"Loop error: {e}")
            if run_once: break
            time.sleep(10)

if __name__ == "__main__":
    main()
