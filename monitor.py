import os
import json
import time
import logging
import winsound
import ctypes
import subprocess
from dotenv import load_dotenv
from indicators import get_indicators
from get_candles import get_candles
from show_positions import show_positions

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("monitor.log"),
        logging.StreamHandler()
    ]
)

PYTHON_EXE = os.path.join("env", "Scripts", "python.exe")

def notify(title, message):
    logging.info(f"NOTIFICATION: {title} - {message}")
    # System Beep
    winsound.Beep(1000, 500)
    # Windows Pop-up (Message Box)
    ctypes.windll.user32.MessageBoxW(0, message, title, 1)

def run_script(script_name, args):
    cmd = [PYTHON_EXE, script_name] + [str(a) for a in args]
    logging.info(f"Executing automation: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logging.error(f"Script error: {result.stderr}")
    else:
        logging.info(f"Script output: {result.stdout}")
    return result

def execute_action(alert):
    action = alert.get("action")
    params = alert.get("action_params", {})
    symbol = alert["symbol"]

    if action == "notify":
        notify(f"ALERT: {alert['id']}", f"Condition met for {symbol}")
    
    elif action == "adjust_sl":
        # 1. Show existing protection orders to find the SL ID
        # For simplicity, we'll try to find all STOP_MARKET orders and cancel them
        # (This is a simplified implementation - in production, we'd be more surgical)
        logging.info(f"Adjusting SL for {symbol} to {params['new_sl']}")
        # We'd need to find the ID, but for now, let's assume we use the tool as-is
        # Note: This is where we'd call cancel_protection.py if we had the ID
        # For this version, we notify and let the user know manual action or further script logic is needed
        notify("ACTION REQUIRED", f"Alert {alert['id']} met. Please adjust SL to {params['new_sl']} manually or expand this script.")

    elif action == "open_long":
        logging.info(f"Opening LONG for {symbol} with qty {params['qty']}")
        run_script("place_order.py", [symbol, "BUY", "MARKET", params['qty'], "LONG"])
        # Set TP/SL if provided
        if "sl" in params:
            run_script("protection_order.py", [symbol, "SELL", "LONG", "STOP", params['sl']])
        if "tp" in params:
            run_script("protection_order.py", [symbol, "SELL", "LONG", "TP", params['tp']])

    elif action == "open_short":
        logging.info(f"Opening SHORT for {symbol} with qty {params['qty']}")
        run_script("place_order.py", [symbol, "SELL", "MARKET", params['qty'], "SHORT"])
        # Set TP/SL if provided
        if "sl" in params:
            run_script("protection_order.py", [symbol, "BUY", "SHORT", "STOP", params['sl']])
        if "tp" in params:
            run_script("protection_order.py", [symbol, "BUY", "SHORT", "TP", params['tp']])

def check_alerts():
    if not os.path.exists("alerts.json"):
        return

    try:
        with open("alerts.json", "r") as f:
            alerts = json.load(f)
    except Exception as e:
        logging.error(f"Error reading alerts.json: {e}")
        return

    active_alerts = [a for a in alerts if a.get("active", False)]
    if not active_alerts:
        return

    # 1. Identify all unique symbols and symbol/interval pairs needed
    symbols = list(set(a["symbol"] for a in active_alerts))
    symbol_intervals = list(set((a["symbol"], a.get("interval", "1h")) for a in active_alerts))
    
    # 2. Pre-fetch all required data
    indicator_data = {} # (symbol, interval) -> data
    position_data = {}  # symbol -> pos_amt
    candle_data = {}    # symbol -> latest price

    # Fetch Indicators
    for sym, interval in symbol_intervals:
        indicator_data[(sym, interval)] = get_indicators(sym, interval)

    # Fetch Positions
    for sym in symbols:
        positions = show_positions(symbol=sym)
        pos_amt = 0
        if positions:
            for p in positions:
                amt = float(p.get("positionAmt", 0)) if isinstance(p, dict) else float(p.position_amt)
                if amt != 0:
                    pos_amt = amt
                    break
        position_data[sym] = pos_amt

    # Fetch Candles (Last)
    for sym in symbols:
        candles = get_candles(symbol=sym, interval="1m", limit=1)
        if candles:
            candle_data[sym] = float(candles[-1][4])

    # 3. Process Alerts using pre-fetched data
    alerts_updated = False
    for alert in active_alerts:
        symbol = alert["symbol"]
        interval = alert.get("interval", "1h")
        condition = alert["condition"]
        
        base_data = indicator_data.get((symbol, interval))
        if not base_data: continue

        # Combine all data into evaluation context
        eval_context = base_data.copy()
        eval_context["pos_amt"] = position_data.get(symbol, 0)
        eval_context["price"] = candle_data.get(symbol, base_data.get("price"))
        
        logging.info(f"Checking {alert['id']} ({condition})")
        
        try:
            if eval(condition, {"__builtins__": None}, eval_context):
                logging.info(f"Condition MET for {alert['id']}!")
                execute_action(alert)
                
                # Deactivate the triggered alert
                alert["active"] = False
                
                # Deactivate other specified alerts
                disables = alert.get("disables", [])
                if disables:
                    for other_id in disables:
                        for a in alerts:
                            if a["id"] == other_id and a["active"]:
                                logging.info(f"Disabling alert {other_id} as requested by {alert['id']}")
                                a["active"] = False
                
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
            if run_once:
                break
            time.sleep(60)
        except KeyboardInterrupt:
            break
        except Exception as e:
            logging.error(f"Loop error: {e}")
            if run_once:
                break
            time.sleep(10)

if __name__ == "__main__":
    main()
