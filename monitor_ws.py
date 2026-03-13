import os
import json
import logging
import subprocess
import asyncio
import hashlib
import time
import threading
from config import get_client
from check_alert import evaluate_alerts, notify

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("monitor_ws.log"),
        logging.StreamHandler()
    ]
)

PYTHON_EXE = os.path.join("env", "Scripts", "python.exe")

# Global state for throttling and execution control
last_realtime_check = 0
last_hedge_check = 0
last_msg_time = time.time()
REALTIME_CHECK_THROTTLE = 1.0  # Seconds between price/position alert checks
HEDGE_CHECK_THROTTLE = 5.0     # Seconds between hedge checks (API intensive)
alert_lock = threading.Lock()

def check_hedge_mode(symbol):
    """
    Checks if a symbol is in 'Hedge Mode' (Both LONG and SHORT positions active).
    If true, it cancels ALL open orders (specifically the Trailing Stop) to prevent
    'naked' exposure if price reverses.
    """
    try:
        client = get_client()
        response = client.rest_api.position_information_v2(symbol=symbol, recv_window=10000)
        positions = response.data()
        
        long_pos = next((p for p in positions if (p.get('positionSide') if isinstance(p, dict) else p.position_side) == 'LONG'), None)
        short_pos = next((p for p in positions if (p.get('positionSide') if isinstance(p, dict) else p.position_side) == 'SHORT'), None)
        
        if long_pos and short_pos:
            long_amt = float(long_pos.get('positionAmt') if isinstance(long_pos, dict) else long_pos.position_amt)
            short_amt = float(short_pos.get('positionAmt') if isinstance(short_pos, dict) else short_pos.position_amt)
            
            if abs(long_amt) > 0 and abs(short_amt) > 0:
                logging.warning(f"HEDGE DETECTED on {symbol}! Cancelling ALL open orders to remove Trailing Stop.")
                client.rest_api.cancel_all_orders(symbol=symbol, recv_window=10000)
                logging.info(f"All orders cancelled for {symbol}. Manual unwind required.")
                
    except Exception as e:
        logging.error(f"Error checking hedge mode for {symbol}: {e}")

def run_alert_check(interval=None, symbol=None, price=None):
    """Runs evaluate_alerts with a lock to ensure single-instance execution."""
    if alert_lock.locked():
        # logging.debug("Alert check already in progress. Skipping.")
        return
    
    with alert_lock:
        try:
            evaluate_alerts(target_interval=interval, ws_symbol=symbol, ws_price=price)
        except Exception as e:
            logging.error(f"Error in evaluate_alerts thread: {e}")

def on_close():
    """Handles WebSocket disconnection by exiting the script."""
    logging.critical("WebSocket connection closed. Exiting monitor.")
    notify("MONITOR CLOSED", "WebSocket connection was closed. Monitor stopped.", notify_type="notify")
    os._exit(1)

def on_error(error):
    """Handles WebSocket errors by exiting the script."""
    logging.critical(f"WebSocket error: {error}. Exiting monitor.")
    notify("MONITOR ERROR", f"WebSocket error: {error}. Monitor stopped.", notify_type="notify")
    os._exit(1)

def on_message(data):
    """
    Handles incoming WebSocket messages from the Binance stream.
    """
    global last_msg_time, last_realtime_check, last_hedge_check
    last_msg_time = time.time()
    try:
        msg_data = data.get("data", {})
        symbol = msg_data.get("s")
        k = msg_data.get("k", {})
        
        if not k:
            return

        interval = k.get("i")
        price = k.get("c")
        k_closed = k.get("x")

        current_time = time.time()

        # 1. Throttled check for "no-interval" alerts (Price/Position only)
        # Only trigger from the 1m stream (or whatever is the fastest) to avoid duplicates if multiple streams are open
        if interval == "1m":
            if current_time - last_realtime_check >= REALTIME_CHECK_THROTTLE:
                threading.Thread(target=run_alert_check, args=(None, symbol, float(price)), daemon=True).start()
                last_realtime_check = current_time
            
            # Check for Hedge Activation (throttled to avoid API limits)
            if current_time - last_hedge_check >= HEDGE_CHECK_THROTTLE:
                 threading.Thread(target=check_hedge_mode, args=(symbol,), daemon=True).start()
                 last_hedge_check = current_time

        # 2. Trigger interval-specific checks only when a candle CLOSES
        if k_closed:
            logging.info(f"CANDLE CLOSED: {symbol} {interval} at price {price}. Triggering interval check.")
            threading.Thread(target=run_alert_check, args=(interval, symbol, float(price)), daemon=True).start()
            
    except Exception as e:
        logging.error(f"Error in on_message: {e}")

def load_alerts(filepath="alerts.json", retries=5, delay=0.1):
    """
    Loads alerts from a JSON file with a retry mechanism to handle file-in-use 
    errors (race conditions) common on Windows when multiple processes access the file.
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

def get_alert_streams():
    """
    Parses 'alerts.json' and generates a list of unique WebSocket stream strings 
    (e.g., 'btcusdt@kline_1m') for all active alerts.
    
    Defaulting: Alerts with no interval specified (null) default to '1m' to 
    ensure high-frequency price monitoring.
    """
    alerts = load_alerts()
    active_streams = set()
    for a in alerts:
        if a.get("active", False):
            symbol = a.get("symbol").lower()
            # Default to 1m for real-time (null) alerts to ensure fast updates
            interval = a.get("interval") or "1m"
            active_streams.add(f"{symbol}@kline_{interval}")
    return list(active_streams)

def get_file_hash(filepath):
    """Calculates the MD5 hash of a file to detect changes in content."""
    if not os.path.exists(filepath):
        return None
    with open(filepath, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()

async def watch_alerts(client, current_streams, current_hash):
    """
    Background task that monitors 'alerts.json' for changes.
    If the file hash changes, it automatically unsubscribes from old streams 
    and subscribes to the updated list of active alert streams.
    """
    while True:
        await asyncio.sleep(10) # Check every 10 seconds
        new_hash = get_file_hash("alerts.json")
        
        if new_hash != current_hash:
            logging.info("Change detected in alerts.json. Updating subscriptions...")
            new_streams = get_alert_streams()
            
            if not new_streams:
                logging.info("No active alerts found. Unsubscribing from all.")
                if current_streams:
                    await client.websocket_streams.unsubscribe(current_streams)
                current_streams = []
            else:
                # Unsubscribe from old, subscribe to new
                if current_streams:
                    await client.websocket_streams.unsubscribe(current_streams)
                
                await client.websocket_streams.subscribe(new_streams)
                
                # Bind message handler to new streams
                for stream in new_streams:
                    client.websocket_streams.on("message", on_message, stream)
                    
                logging.info(f"Updated subscriptions: {new_streams}")
                current_streams = new_streams
            
            current_hash = new_hash

async def connection_health_check(client):
    """
    Periodically checks if the WebSocket connection is still active.
    Exits the script if the connection is closed or unresponsive.
    """
    global last_msg_time
    while True:
        await asyncio.sleep(5)
        current_time = time.time()
        
        if not hasattr(client, 'websocket_streams') or not client.websocket_streams.connections:
            # If we expect to be running but have no connections, check if it's been too long
            active_streams = get_alert_streams()
            if active_streams and current_time - last_msg_time > 60:
                logging.critical("No WebSocket connections found despite active alerts. Exiting.")
                notify("MONITOR FAILURE", "WebSocket connection lost. Monitor stopped.", notify_type="notify")
                os._exit(1)
            continue
        
        # Check for explicitly closed connections
        for conn in client.websocket_streams.connections:
            if conn.websocket.closed:
                logging.critical(f"WebSocket connection {conn.id} is closed. Exiting.")
                notify("MONITOR CLOSED", "WebSocket connection was closed. Monitor stopped.", notify_type="notify")
                os._exit(1)
        
        # Unresponsiveness Check: If we have active streams but no messages
        active_streams = get_alert_streams()
        if active_streams:
            silence_duration = current_time - last_msg_time
            
            # If silent for 30s, try a proactive ping
            if silence_duration > 30:
                try:
                    for conn in client.websocket_streams.connections:
                        await client.websocket_streams.ping_server(conn)
                    logging.debug("Proactive ping sent due to silence.")
                except Exception as e:
                    logging.critical(f"Ping failed: {e}. Connection is likely dead.")
                    notify("MONITOR TIMEOUT", "WebSocket connection unresponsive. Monitor stopped.", notify_type="notify")
                    os._exit(1)
            
            # If silent for 60s, assume dead regardless of ping (Binance kline streams are very chatty)
            if silence_duration > 60:
                logging.critical("WebSocket unresponsiveness (60s silence). Exiting.")
                notify("MONITOR TIMEOUT", "WebSocket connection timed out. Monitor stopped.", notify_type="notify")
                os._exit(1)

async def main():
    """
    Main entry point for the WebSocket Monitor.
    - Initializes the Binance client and WebSocket connection.
    - Subscribes to initial streams from 'alerts.json'.
    - Starts the background 'watch_alerts' and 'connection_health_check' tasks.
    """
    client = get_client()
    
    current_hash = get_file_hash("alerts.json")
    current_streams = get_alert_streams()

    # Define tasks for finally block access
    watcher = None
    health_check = None

    try:
        # Always create connection to allow for dynamic subscription updates
        await client.websocket_streams.create_connection()
        
        if not current_streams:
            logging.info("No active alerts found in alerts.json. Waiting for changes...")
        else:
            logging.info(f"Initial subscription: {current_streams}")
            await client.websocket_streams.subscribe(current_streams)
            
            # Bind message handler to EACH stream
            for stream in current_streams:
                client.websocket_streams.on("message", on_message, stream)

        # Start background tasks
        watcher = asyncio.create_task(watch_alerts(client, current_streams, current_hash))
        health_check = asyncio.create_task(connection_health_check(client))

        logging.info("WebSocket Monitor Started. Press Ctrl+C to stop.")
        await asyncio.Future()
    except asyncio.CancelledError:
        pass
    finally:
        logging.info("Shutting down monitor gracefully...")
        if watcher: watcher.cancel()
        if health_check: health_check.cancel()
        
        try:
            if watcher: await watcher
            if health_check: await health_check
        except asyncio.CancelledError:
            pass
        
        # Properly close the WebSocket connection
        if hasattr(client, 'websocket_streams'):
            await client.websocket_streams.close_connection()
            logging.info("WebSocket connection closed.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass # main()'s finally block handles the cleanup
    except Exception as e:
        logging.critical(f"Monitor crashed: {e}")
        notify("MONITOR CRASHED", f"Monitor exited unexpectedly: {e}", notify_type="notify")
