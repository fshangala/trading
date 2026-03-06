import os
import json
import time
import logging
import winsound
import ctypes
import subprocess
from dotenv import load_dotenv
from indicators import get_indicators

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

from binance_sdk_derivatives_trading_usds_futures.derivatives_trading_usds_futures import DerivativesTradingUsdsFutures
from binance_common.configuration import ConfigurationRestAPI

def check_alerts():
    if not os.path.exists("alerts.json"):
        return

    try:
        with open("alerts.json", "r") as f:
            alerts = json.load(f)
    except Exception as e:
        logging.error(f"Error reading alerts.json: {e}")
        return

    # Fetch current prices/indicators to avoid duplicate API calls
    # For now, we call get_indicators per unique symbol/interval
    
    for alert in alerts:
        if not alert.get("active", False):
            continue

        symbol = alert["symbol"]
        interval = alert.get("interval", "1h")
        condition = alert["condition"]
        
        logging.info(f"Checking {alert['id']} ({condition})")
        
        data = get_indicators(symbol, interval)
        if not data: continue
        
        # Get current price
        from binance_sdk_derivatives_trading_usds_futures.derivatives_trading_usds_futures import DerivativesTradingUsdsFutures
        from binance_common.configuration import ConfigurationRestAPI
        
        config = ConfigurationRestAPI(
            api_key=os.getenv("BINANCE_API_KEY", ""),
            api_secret=os.getenv("BINANCE_API_SECRET", ""),
            base_path="https://demo-fapi.binance.com/",
        )
        client = DerivativesTradingUsdsFutures(config_rest_api=config)
        
        try:
            price_res = client.rest_api.kline_candlestick_data(symbol=symbol, interval="1m", limit=1)
            data["price"] = float(price_res.data()[-1][4])
            
            # Fetch position amount for the symbol
            pos_res = client.rest_api.position_information_v2(symbol=symbol)
            pos_amt = 0
            for p in pos_res.data():
                amt = float(p.get("positionAmt", 0))
                if amt != 0:
                    pos_amt = amt
                    break
            data["pos_amt"] = pos_amt
            
            if eval(condition, {"__builtins__": None}, data):
                logging.info(f"Condition MET for {alert['id']}!")
                execute_action(alert)
                # Deactivate alert to prevent spamming
                alert["active"] = False
                with open("alerts.json", "w") as f:
                    json.dump(alerts, f, indent=4)
                    
        except Exception as e:
            logging.error(f"Error evaluating alert {alert['id']}: {e}")

def main():
    logging.info("Background Monitor Active.")
    while True:
        try:
            check_alerts()
            time.sleep(60)
        except KeyboardInterrupt:
            break
        except Exception as e:
            logging.error(f"Loop error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
