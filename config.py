import os
from dotenv import load_dotenv, find_dotenv

# Load explicitly
env_file = find_dotenv()
load_dotenv(env_file, override=True)

def get_config():
    """
    Returns API keys and base path based on the TESTNET environment variable.
    """
    # Check if TESTNET is set to "true"
    use_testnet = os.getenv("TESTNET", "true").lower() == "true"
    
    if use_testnet:
        return {
            "api_key": os.getenv("BINANCE_TESTNET_API_KEY"),
            "api_secret": os.getenv("BINANCE_TESTNET_API_SECRET"),
            "base_path": "https://demo-fapi.binance.com/",
            "is_testnet": True
        }
    else:
        return {
            "api_key": os.getenv("BINANCE_API_KEY"),
            "api_secret": os.getenv("BINANCE_API_SECRET"),
            "base_path": "https://fapi.binance.com/",
            "is_testnet": False
        }


if __name__ == "__main__":
    config = get_config()
    env_name = "TESTNET" if config["is_testnet"] else "LIVE"
    print(f"Current Environment: {env_name}")
    print(f"Base Path:           {config['base_path']}")
    # Print partial key for verification
    key = config['api_key']
    if key:
        print(f"API Key:             {key[:5]}...{key[-5:]}")
    else:
        print("API Key:             Not Found")
