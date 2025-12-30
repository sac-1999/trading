from broker import Broker_websocket
from logging import Logger

logger = Logger(__name__)

def on_open(self, wsapp):
    logger.info("WebSocket opened")
    # token_list1 = [
    #     {
    #     "action": 0,
    #     "exchangeType": 1,
    #     "tokens": ["26009"]
    #     }
    # ]
    # self.sws.subscribe('1234', 2, token_list1)

def on_data(wsapp, message):
    logger.info(f"Tick: {message}")

def on_error(self, wsapp, error):
    logger.error(f"WS error: {error}")

def on_close(self, wsapp):
    logger.warning("WebSocket closed")

def close_connection(self):
    self.sws.close_connection()

broker_socket = Broker_websocket()
broker_socket.sws.on_open = on_open
broker_socket.sws.on_data = on_data
broker_socket.sws.on_error = on_error
broker_socket.sws.on_close = on_close
broker_socket.sws.connect()

