
##angle one account
from SmartApi import SmartConnect
from SmartApi import SmartConnect
from SmartApi.smartWebSocketV2 import SmartWebSocketV2
import pyotp
import time
import utils
from dotenv import load_dotenv
import os
import pandas as pd

def load_config():
    env_path = os.getenv('BROKER_ENV_FILE_PATH', os.path.join(os.getcwd(), ".env"))
    if os.path.exists(env_path):
        load_dotenv(env_path)
    else:
        raise FileNotFoundError(f"Env file missing for Broker at {env_path}")

    return {
        "BROKERCONFIG": {
            "api_key": os.getenv("INTRA_API_KEY"),
            "secret_key": os.getenv("INTRA_SECRET_KEY"),
            "pin": os.getenv("INTRA_PIN"),
            "clientId": os.getenv("INTRA_CLIENT_ID"),
            "angletoken": os.getenv("ANGLETOKEN"),
            "websocket_api_key":os.getenv("WEBSOCKET_API_KEY"),
            "websocket_secret_key":os.getenv("WEBSOCKET_API_SECRET_KEY")
        },
        "TELEGRAM": {
            "token": os.getenv("TELEGRAM_TOKEN"),
            "chatid": os.getenv("TELEGRAM_CHATID"),
        }
    }




class Broker:
    def __init__(self):
        conf = load_config()['BROKERCONFIG']

        self.apikey = conf["api_key"]
        self.pin = conf["pin"]
        self.clientid = conf["clientId"]
        self.angletoken = conf["angletoken"]
        self.smartapi = None
        self.connect()

    def connect(self):
        self.smartapi = SmartConnect(self.apikey)
        totp=pyotp.TOTP(self.angletoken).now()
        session = self.smartapi.generateSession(self.clientid, self.pin, totp)
        if(session.get("status")):
            refreshtoken = session['data']['refreshToken']
            connection_status = self.smartapi.generateToken(refreshtoken)
            if(connection_status["status"]):
                return True
        return False

    def place_order(self, symbol, qty, order_type, side, price=None, stop_loss=None, target=None):
        print(f"AngelOne order: {side} {qty} of {symbol}")

    def get_balance(self):
        return {"INR": 50000}

    def get_position(self, symbol):
        return {"symbol": symbol, "qty": 100, "avg_price": 900}

    def close_position(self, symbol):
        print(f"Closing {symbol} in AngelOne")

    def get_candle_stick_data(self, exchange, symbol, timeframe, startdate, enddate,  isindex):
        token = None
        if isindex:
            token = utils.get_token(exchange, symbol)
        else:
            token = utils.get_token(exchange, symbol + '-EQ')
   
        historicParam = {
        "stock": symbol,
        "exchange": exchange,
        "symboltoken": token,
        "interval": timeframe,
        "fromdate": startdate.strftime("%Y-%m-%d %H:%M"),
        "todate": enddate.strftime("%Y-%m-%d %H:%M")
        }

        retry_count = 0
        while(retry_count < 5):
            try:
                res = self.smartapi.getCandleData(historicParam)
                data = pd.DataFrame(res['data'], columns=["timestamp", "open", "high", "low", "close", "volume"])
                return data[["timestamp", "open", "high", "low", "close", "volume"]]
                
            except Exception as e:
                print("Warning : ",str(e))
                retry_count += 1
                time.sleep(1)
                print('retrying after a pause of 1 sec ....')
                continue

            
class Broker_websocket:
    def __init__(self):
        conf = load_config()['BROKERCONFIG']
        self.apikey = conf["websocket_api_key"]
        self.pin = conf["pin"]
        self.clientid = conf["clientId"]
        self.angletoken = conf["angletoken"]
        self.smartapi = None
        self.sws = None
        self.connect()

    def connect(self):
        self.smartapi = SmartConnect(self.apikey)
        totp=pyotp.TOTP(self.angletoken).now()
        session = self.smartapi.generateSession(self.clientid, self.pin, totp)
        if(session.get("status")):
            AUTH_TOKEN = session["data"]["jwtToken"]
            FEED_TOKEN = self.smartapi.getfeedToken() 
            self.sws = SmartWebSocketV2(
                auth_token=AUTH_TOKEN,
                api_key=self.apikey,
                client_code=self.clientid,
                feed_token=FEED_TOKEN,
                max_retry_attempt=3,      # optional
                retry_strategy=1,         # exponential backoff
                retry_delay=5,
                retry_multiplier=2
                )
           
        if not session.get("status"):
            raise RuntimeError(f"Login failed: {session}")
        


  