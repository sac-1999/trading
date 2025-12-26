from crypto.broker import DeltaExchange
from crypto.manager.broker_websocket import DeltaWebSocketClient
from dotenv import load_dotenv
from crypto.logger_config import get_logger
import os 
import time
logger = get_logger(__name__)

load_dotenv()

USE_TESTNET = False
broker = DeltaExchange()
logger.info("=" * 60)
delta_websocket = DeltaWebSocketClient(testnet=USE_TESTNET)
client_thread = delta_websocket.start()


def reset_all_clients():
    global delta_websocket, broker
    delta_websocket.stop()
    del broker
    del delta_websocket
    broker = DeltaExchange()
    logger.info("=" * 60)
    delta_websocket = DeltaWebSocketClient(testnet=USE_TESTNET)
    client_thread = delta_websocket.start()

    
def active_positions(symbol):
    if delta_websocket:
        positions = delta_websocket.positions
        if positions.get(symbol) is None:
            return False
        


def start_trading():
    #check any active position
    #check any pending order
    #cancel all limit order
    #look if we need any trade
    #place a limit order
    #signal when limit order executed
    #place bracket order
    #

    #if there is any active position
    pass



# balance = broker.get_balance()
# if not balance:
#     logger.critical(f"Balance data is Missing")
#     raise ("Unable to find the balance")

# balance = float(balance)

# logger.info(F"Trading Amount : {balance} $.")
# minbalance = 0
# symbol = 'BTCUSD'
# if balance <= minbalance:
#     logger.critical(f"Balance is Less than {minbalance}")
#     raise(f"Balance is Less than {minbalance}")

# broker.place_bracket_order(symbol, 1, 85000, 92000)
# broker.place_order(symbol, 'buy', 1, 'LIMIT', 87000, reduce_only=True)  
        
# ema_len = 11
# data = broker.get_historical_data(symbol)
# data = Indicators.ema(data, ema_len, 'ema')
# data = data.dropna()
# data.reset_index(inplace = True, drop = True)
# data = Strategy.time_5_ema_11(data, f"ema_{ema_len}" )
# logger.info(data[data['sell'] | data['buy']])

# last_candle = data.iloc[-1]
# tradentry , side = broker.get_active_positions(symbol)
# if tradentry:
#     logger.info(tradentry, side)

time.sleep(5)
# reset_all_clients()
active_positions('BTCUSD')
time.sleep(10000)