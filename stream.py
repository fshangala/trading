from dotenv import load_dotenv
import os, logging, asyncio

load_dotenv()
logging.basicConfig(level=logging.INFO)

from binance_common.configuration import ConfigurationRestAPI, ConfigurationWebSocketStreams
from binance_common.constants import DERIVATIVES_TRADING_USDS_FUTURES_WS_STREAMS_TESTNET_URL
from binance_sdk_derivatives_trading_usds_futures.derivatives_trading_usds_futures import DerivativesTradingUsdsFutures
from binance_sdk_derivatives_trading_usds_futures.rest_api.models import (
    NewOrderSideEnum,
    NewOrderPositionSideEnum,
    NewOrderTimeInForceEnum
)

config_ws = ConfigurationWebSocketStreams(
    stream_url=DERIVATIVES_TRADING_USDS_FUTURES_WS_STREAMS_TESTNET_URL,
)

config_rest = ConfigurationRestAPI(
    api_key=os.getenv("BINANCE_API_KEY", ""),
    api_secret=os.getenv("BINANCE_API_SECRET", ""),
    base_path="https://demo-fapi.binance.com/",
)

client = DerivativesTradingUsdsFutures(config_ws_streams=config_ws, config_rest_api=config_rest)

order_x = None
order_y = None
order_loss = None
def open_position():
    global order_x, order_y
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
    order_x = data2
    
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
    order_y = data4

def close_position(mark_price, loss, long=True):

    global order_x, order_y, order_loss
    if order_x is None or order_y is None:
        logging.warning("close_position called but no open positions found.")
        return

    try:
        # Close the LONG position (order_x) with a LIMIT SELL order
        logging.info(f"Closing {'LONG' if long else 'SHORT'} position for {order_x['symbol']} at limit price {mark_price}")
        close_1_response = client.rest_api.new_order(
            symbol=order_x['symbol'],
            side=NewOrderSideEnum.SELL if long else NewOrderSideEnum.BUY,
            position_side=NewOrderPositionSideEnum.LONG if long else NewOrderPositionSideEnum.SHORT,
            type="LIMIT",
            price=round(mark_price, 1),
            quantity=float(order_x['origQty']),
            time_in_force=NewOrderTimeInForceEnum.GTC
        )
        logging.info(f"Close {'LONG' if long else 'SHORT'} order placed: {close_1_response.data().client_order_id}")        

        # Close the SHORT position (order_y) with a LIMIT BUY order
        close_2_price = mark_price - 1.01*mark_price if long else mark_price + 1.01*mark_price
        logging.info(f"Closing {'SHORT' if long else 'LONG'} position for {order_y['symbol']} at limit price {close_2_price}")
        close_y_response = client.rest_api.new_order(
            symbol=order_y['symbol'],
            side=NewOrderSideEnum.BUY if long else NewOrderSideEnum.SELL,
            position_side=NewOrderPositionSideEnum.SHORT if long else NewOrderPositionSideEnum.LONG,
            type="LIMIT",
            price=round(close_2_price, 1),
            quantity=float(order_y['origQty']),
            time_in_force=NewOrderTimeInForceEnum.GTC
        )
        logging.info(f"Close {'SHORT' if long else 'LONG'} order placed: {close_y_response.data().client_order_id}")

        order_loss_response = client.rest_api.query_order(
            symbol=order_y['symbol'],
            orig_client_order_id=close_y_response.data().client_order_id
        )
        order_loss = order_loss_response.data()
        logging.info(f"Order loss: {order_loss["clientOrderId"]}")

    except Exception as e:
        logging.error(f"Error closing position: {e}")


def trade(data):
    global order_x, order_y, order_loss
    mark_price = float(data.p)
    if order_x is None and order_y is None:
        open_position()
        return

    if order_x is not None and order_y is not None:

        order_x_price = float(order_x["avgPrice"])
        order_y_price = float(order_y["avgPrice"])
        
        x_gain = mark_price - order_x_price
        y_gain = order_y_price - mark_price
        loss = order_x_price - order_y_price

        if order_loss is None:
            if mark_price > (order_x_price + (order_x_price * 0.001)) and x_gain > 0:
                close_position(mark_price, loss)
            elif mark_price < (order_y_price - (order_y_price * 0.001)) and y_gain > 0:
                close_position(mark_price, loss, long=False)
        else:
            response = client.rest_api.query_order(
                symbol="BTCUSDT",
                orig_client_order_id=order_loss["clientOrderId"]
            )
            data = response.data()
            if data["status"] == "FILLED":
                order_loss = None
                order_x = None
                order_y = None


        print(x_gain, loss, y_gain)


async def main():
    connection = await client.websocket_streams.create_connection()
    try:
        if connection is not None:
            stream = await connection.mark_price_stream(symbol="BTCUSDT")
            stream.on('message', trade)
            # Keep the script running to receive messages until interrupted.
            await asyncio.Event().wait()
    except KeyboardInterrupt:
        logging.info("Interruption received, shutting down.")
    except Exception as e:
        logging.error(e)
    finally:
        if connection is not None:
            logging.info("Closing connection.")
            await connection.close_connection(close_session=True)

if __name__ == "__main__":
    asyncio.run(main())
