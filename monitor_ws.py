"""
Binance Futures WebSocket Monitor

This script provides real-time monitoring of Binance USDS-M Futures markets using WebSockets.
It integrates with 'alerts.json' to trigger automated notifications or actions based on 
price movements, technical indicators, and position state changes.

Monitoring Philosophy:
- High-frequency message handling via per-stream 'on_message' subscriptions.
- Proactive connection health monitoring (pings/timeouts) via background asyncio tasks.
- Graceful shutdown and recovery managed through exception handling and asyncio events.

Usage:
    .\\env\\Scripts\\python.exe monitor_ws.py
"""

import os
import json
import logging
import asyncio
import hashlib
import time
import threading
from config import get_client
from check_alert import evaluate_alerts, notify

# Global state for throttling and execution control
last_realtime_checks = {}  # format: { symbol: timestamp }
last_hedge_checks = {}     # format: { symbol: timestamp }
last_msg_time = time.time()
REALTIME_CHECK_THROTTLE = 1.0  # Seconds between price/position alert checks
HEDGE_CHECK_THROTTLE = 5.0     # Seconds between hedge checks (API intensive)
alert_lock = threading.Lock()

# Event used to signal a graceful shutdown from callbacks or tasks
shutdown_event = None
main_loop = None

# Tracking position states to detect closures/changes
# format: { symbol: { 'LONG': amt, 'SHORT': amt, 'state': 'NONE|LONG|SHORT|HEDGE' } }
pos_tracker = {}

def trigger_shutdown(reason):
    """
    Signals the main loop to shut down gracefully.

    Args:
        reason (str): The reason for triggering the shutdown (logged for audit).
    """
    global shutdown_event, main_loop
    logging.critical(f"Shutdown triggered: {reason}")
    if shutdown_event and main_loop:
        main_loop.call_soon_threadsafe(shutdown_event.set)

def check_position_state(symbol):
    """
    Fetches the current position state from the API and detects transitions.
    
    Identifies state changes (e.g., closure or hedge activation) and triggers 
    priority alert checks or safety actions (like cancelling orders).

    Args:
        symbol (str): The trading pair symbol to check.
    """
    global pos_tracker
    try:
        client = get_client()
        response = client.rest_api.position_information_v2(symbol=symbol, recv_window=10000)
        positions = response.data()
        
        long_pos = next((p for p in positions if (p.get('positionSide') if isinstance(p, dict) else p.position_side) == 'LONG'), None)
        short_pos = next((p for p in positions if (p.get('positionSide') if isinstance(p, dict) else p.position_side) == 'SHORT'), None)
        
        long_amt = float(long_pos.get('positionAmt') if isinstance(long_pos, dict) else long_pos.position_amt) if long_pos else 0.0
        short_amt = float(short_pos.get('positionAmt') if isinstance(short_pos, dict) else short_pos.position_amt) if short_pos else 0.0
        
        current_state = 'NONE'
        if abs(long_amt) > 0 and abs(short_amt) > 0: current_state = 'HEDGE'
        elif abs(long_amt) > 0: current_state = 'LONG'
        elif abs(short_amt) > 0: current_state = 'SHORT'
        
        prev_data = pos_tracker.get(symbol, {'state': 'UNKNOWN', 'LONG': 0.0, 'SHORT': 0.0})
        prev_state = prev_data['state']
        
        if current_state != prev_state and prev_state != 'UNKNOWN':
            logging.info(f"POSITION CHANGE on {symbol}: {prev_state} -> {current_state}")
            
            if current_state == 'NONE':
                logging.info(f"Position CLOSED on {symbol}. Triggering priority alert check.")
                threading.Thread(target=run_alert_check, args=(None, symbol, None), daemon=True).start()
            
            if current_state == 'HEDGE':
                logging.warning(f"HEDGE DETECTED on {symbol}! Cancelling ALL open orders to remove Trailing Stop.")
                client.rest_api.cancel_all_orders(symbol=symbol, recv_window=10000)
                logging.info(f"All orders cancelled for {symbol}. Manual unwind required.")
                threading.Thread(target=run_alert_check, args=(None, symbol, None), daemon=True).start()

        pos_tracker[symbol] = {'state': current_state, 'LONG': long_amt, 'SHORT': short_amt}
                
    except Exception as e:
        logging.error(f"Error checking position state for {symbol}: {e}")

def run_alert_check(interval=None, symbol=None, price=None):
    """
    Executes the alert evaluation logic within a thread-safe lock.

    Args:
        interval (str, optional): The timeframe of the candle that triggered the check.
        symbol (str, optional): The symbol that received an update.
        price (float, optional): The latest price from the WebSocket message.
    """
    if alert_lock.locked():
        return
    
    with alert_lock:
        try:
            evaluate_alerts(target_interval=interval, ws_symbol=symbol, ws_price=price)
        except Exception as e:
            logging.error(f"Error in evaluate_alerts thread: {e}")

def on_message(data):
    """
    Handles incoming WebSocket messages from the Binance stream.
    
    Routes data to throttled real-time checks or interval-based checks 
    (on candle close).

    Args:
        data (str|dict): The raw message data from the WebSocket.
    """
    global last_msg_time, last_realtime_checks, last_hedge_checks
    last_msg_time = time.time()
    try:
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                return

        msg_data = data.get("data", data) if isinstance(data, dict) else {}
        symbol = msg_data.get("s")
        if not symbol: return

        k = msg_data.get("k", {})
        if not k: return

        interval = k.get("i")
        price = k.get("c")
        k_closed = k.get("x")

        current_time = time.time()

        if interval == "1m":
            last_rc = last_realtime_checks.get(symbol, 0)
            if current_time - last_rc >= REALTIME_CHECK_THROTTLE:
                last_realtime_checks[symbol] = current_time
                threading.Thread(target=run_alert_check, args=(None, symbol, float(price)), daemon=True).start()
            
            last_hc = last_hedge_checks.get(symbol, 0)
            if current_time - last_hc >= HEDGE_CHECK_THROTTLE:
                 last_hedge_checks[symbol] = current_time
                 threading.Thread(target=check_position_state, args=(symbol,), daemon=True).start()

        if k_closed:
            logging.info(f"CANDLE CLOSED: {symbol} {interval} at price {price}. Triggering interval check.")
            threading.Thread(target=run_alert_check, args=(interval, symbol, float(price)), daemon=True).start()
            
    except Exception as e:
        logging.error(f"Error in on_message: {e}")

def load_alerts(filepath="alerts.json", retries=5, delay=0.1):
    """
    Loads alerts from a JSON file with a retry mechanism.

    Args:
        filepath (str): Path to the JSON file.
        retries (int): Number of attempts.
        delay (float): Seconds between attempts.

    Returns:
        list: The list of alert objects.
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
    return []

def get_alert_streams():
    """
    Parses 'alerts.json' to generate a list of unique WebSocket stream strings.

    Returns:
        list: A list of streams (e.g., ['btcusdt@kline_1m']).
    """
    alerts = load_alerts()
    active_streams = set()
    for a in alerts:
        if a.get("active", False):
            symbol = a.get("symbol").lower()
            interval = a.get("interval") or "1m"
            active_streams.add(f"{symbol}@kline_{interval}")
    return list(active_streams)

def get_file_hash(filepath):
    """
    Calculates the MD5 hash of a file to detect content changes.

    Args:
        filepath (str): Path to the file.

    Returns:
        str|None: The hex digest of the hash.
    """
    if not os.path.exists(filepath):
        return None
    with open(filepath, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()

async def watch_alerts(client, current_streams, current_hash):
    """
    Background task that monitors 'alerts.json' for changes.

    Args:
        client (Client): The Binance SDK client.
        current_streams (list): The currently active list of streams.
        current_hash (str): The current hash of alerts.json.
    """
    while True:
        await asyncio.sleep(10)
        new_hash = get_file_hash("alerts.json")
        
        if new_hash != current_hash:
            logging.info("Change detected in alerts.json. Updating subscriptions...")
            new_streams = get_alert_streams()
            
            to_unsubscribe = list(set(current_streams) - set(new_streams))
            to_subscribe = list(set(new_streams) - set(current_streams))
            
            if to_unsubscribe:
                logging.info(f"Unsubscribing from old streams: {to_unsubscribe}")
                await client.websocket_streams.unsubscribe(to_unsubscribe)
            
            if to_subscribe:
                logging.info(f"Subscribing to new streams: {to_subscribe}")
                await client.websocket_streams.subscribe(to_subscribe)
                for stream in to_subscribe:
                    client.websocket_streams.on("message", on_message, stream)
            
            current_streams = new_streams
            current_hash = new_hash

async def connection_health_check(client):
    """
    Periodically checks if the WebSocket connection is still active.

    Args:
        client (Client): The Binance SDK client.
    """
    global last_msg_time
    while True:
        await asyncio.sleep(5)
        current_time = time.time()
        
        if not hasattr(client, 'websocket_streams') or not client.websocket_streams.connections:
            active_streams = get_alert_streams()
            if active_streams and current_time - last_msg_time > 60:
                trigger_shutdown("No WebSocket connections found despite active alerts.")
                return
            continue
        
        active_streams = get_alert_streams()
        if active_streams:
            silence_duration = current_time - last_msg_time
            if silence_duration > 30:
                try:
                    for conn in client.websocket_streams.connections:
                        await client.websocket_streams.ping_server(conn)
                except Exception as e:
                    trigger_shutdown(f"Ping failed: {e}. Connection is likely dead.")
                    return
            
            if silence_duration > 60:
                trigger_shutdown("WebSocket unresponsiveness (60s silence).")
                return

async def main():
    """
    Main entry point for the WebSocket Monitor.
    """
    global shutdown_event, main_loop
    
    client = get_client()
    main_loop = asyncio.get_event_loop()
    shutdown_event = asyncio.Event()
    
    current_hash = get_file_hash("alerts.json")
    current_streams = get_alert_streams()

    watcher = None
    health_check = None

    try:
        await client.websocket_streams.create_connection()
        
        if current_streams:
            logging.info(f"Initial subscription: {current_streams}")
            await client.websocket_streams.subscribe(current_streams)
            for stream in current_streams:
                client.websocket_streams.on("message", on_message, stream)
        else:
            logging.info("No active alerts found. Waiting for changes...")

        watcher = asyncio.create_task(watch_alerts(client, current_streams, current_hash))
        health_check = asyncio.create_task(connection_health_check(client))

        logging.info("WebSocket Monitor Started. Press Ctrl+C to stop.")
        await shutdown_event.wait()
        
    except asyncio.CancelledError:
        pass
    finally:
        logging.info("Shutting down monitor gracefully...")
        if watcher: watcher.cancel()
        if health_check: health_check.cancel()
        
        if hasattr(client, 'websocket_streams'):
            await client.websocket_streams.close_connection()
            logging.info("WebSocket connection closed.")

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("monitor_ws.log"),
            logging.StreamHandler()
        ]
    )

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logging.critical(f"Monitor crashed: {e}")
        notify("MONITOR CRASHED", f"Monitor exited unexpectedly: {e}", notify_type="notify")
