from dotenv import load_dotenv
import os, logging

load_dotenv()
logging.basicConfig(level=logging.INFO)

from binance_sdk_derivatives_trading_usds_futures.derivatives_trading_usds_futures import DerivativesTradingUsdsFutures
from binance_sdk_derivatives_trading_usds_futures.rest_api.models import (
    NewOrderSideEnum,
    NewOrderPositionSideEnum,
    NewOrderTimeInForceEnum
)
from binance_common.configuration import ConfigurationRestAPI
from binance_common.constants import DERIVATIVES_TRADING_USDS_FUTURES_REST_API_TESTNET_URL

configuration = ConfigurationRestAPI(
    api_key=os.getenv("BINANCE_API_KEY", ""),
    api_secret=os.getenv("BINANCE_API_SECRET", ""),
    base_path="https://demo-fapi.binance.com/",
)

client = DerivativesTradingUsdsFutures(config_rest_api=configuration)

try:
    response = client.rest_api.new_order(
        symbol="BTCUSDT",
        side=NewOrderSideEnum.BUY,
        position_side=NewOrderPositionSideEnum.LONG,
        type="MARKET",
        quantity=0.002
    )
    data1 = response.data()
    logging.info(f"New order: {data1.client_order_id}")

    response = client.rest_api.query_order(
        symbol="BTCUSDT",
        orig_client_order_id=data1.client_order_id
    )
    data2 = response.data()
    logging.info(data2)
    
    price = float(data2["avgPrice"])
    response = client.rest_api.new_order(
        symbol="BTCUSDT",
        side=NewOrderSideEnum.SELL,
        position_side=NewOrderPositionSideEnum.SHORT,
        type="LIMIT",
        price=round(price - price*0.01,1),
        quantity=0.002,
        time_in_force=NewOrderTimeInForceEnum.GTC
    )
    data3 = response.data()
    logging.info(f"New order: {data3.client_order_id}")

    response = client.rest_api.query_order(
        symbol="BTCUSDT",
        orig_client_order_id=data3.client_order_id
    )
    data4 = response.data()
    logging.info(data4)

except Exception as e:
    logging.error(e)