import os
import sys
from dotenv import load_dotenv, find_dotenv

# Load explicitly
env_file = find_dotenv()
load_dotenv(env_file, override=True)

from binance_sdk_derivatives_trading_usds_futures.derivatives_trading_usds_futures import DerivativesTradingUsdsFutures
from binance_common.configuration import ConfigurationRestAPI, ConfigurationWebSocketStreams
from binance_common.constants import (
    DERIVATIVES_TRADING_USDS_FUTURES_WS_STREAMS_TESTNET_URL,
    DERIVATIVES_TRADING_USDS_FUTURES_WS_STREAMS_PROD_URL
)

def get_config():
    """
    Retrieves API keys, environment settings, and proxy configuration from environment variables.

    Environment Variables:
    - TESTNET: 'true' (default) or 'false'.
    - USE_PROXY: 'true' or 'false'.
    - BINANCE_API_PROXY_HOST, BINANCE_API_PROXY_PORT, etc.

    Returns:
    - dict: Configuration dictionary with api_key, api_secret, base_path, stream_url, proxy, and is_testnet.
    """
    # Check if TESTNET is set to "true"
    use_testnet = os.getenv("TESTNET", "true").lower() == "true"
    use_proxy = os.getenv("USE_PROXY", "false").lower() == "true"

    proxy_dict = None
    if use_proxy:
        host = os.getenv("BINANCE_API_PROXY_HOST")
        port = os.getenv("BINANCE_API_PROXY_PORT")
        protocol = os.getenv("BINANCE_API_PROXY_PROTOCOL", "http")
        username = os.getenv("BINANCE_API_PROXY_USERNAME")
        password = os.getenv("BINANCE_API_PROXY_PASSWORD")

        if host and port:
            proxy_dict = {
                "host": host,
                "port": port,
                "protocol": protocol
            }
            if username and password:
                proxy_dict["auth"] = {
                    "username": username,
                    "password": password
                }

    if use_testnet:
        return {
            "api_key": os.getenv("BINANCE_TESTNET_API_KEY"),
            "api_secret": os.getenv("BINANCE_TESTNET_API_SECRET"),
            "base_path": "https://demo-fapi.binance.com/",
            "stream_url": DERIVATIVES_TRADING_USDS_FUTURES_WS_STREAMS_TESTNET_URL,
            "proxy": proxy_dict if use_proxy else None,
            "is_testnet": True
        }
    else:
        return {
            "api_key": os.getenv("BINANCE_API_KEY"),
            "api_secret": os.getenv("BINANCE_API_SECRET"),
            "base_path": os.getenv("BINANCE_API_PROXY_URL", "https://fapi.binance.com/"),
            "stream_url": DERIVATIVES_TRADING_USDS_FUTURES_WS_STREAMS_PROD_URL,
            "proxy": proxy_dict if use_proxy else None,
            "is_testnet": False
        }

def get_client():
    """
    Initializes and returns a configured DerivativesTradingUsdsFutures client for Binance REST API and WebSocket streams.

    Returns:
    - DerivativesTradingUsdsFutures: The initialized client object.
    """
    config_data = get_config()

    config_rest = ConfigurationRestAPI(
        api_key=config_data['api_key'],
        api_secret=config_data['api_secret'],
        base_path=config_data['base_path'],
        proxy=config_data.get('proxy')
    )

    config_ws = ConfigurationWebSocketStreams(
        stream_url=config_data['stream_url'],
        proxy=config_data.get('proxy')
    )

    return DerivativesTradingUsdsFutures(
        config_rest_api=config_rest,
        config_ws_streams=config_ws
    )

if __name__ == "__main__":
    config = get_config()
    env_name = "TESTNET" if config["is_testnet"] else "LIVE"
    
    print("\n--- Binance Futures Configuration Check ---")
    print(f"Environment:   {env_name}")
    print(f"Base Path:     {config['base_path']}")
    print(f"Stream URL:    {config['stream_url']}")
    
    # Print partial key for verification
    key = config['api_key']
    if key:
        print(f"API Key:       {key[:5]}...{key[-5:]}")
    else:
        print("API Key:       NOT FOUND")
        
    if config['proxy']:
        print(f"Proxy Status:  ACTIVE ({config['proxy']['host']}:{config['proxy']['port']})")
    else:
        print(f"Proxy Status:  INACTIVE")
    print("-------------------------------------------\n")
