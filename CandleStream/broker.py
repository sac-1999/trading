
##angle one account
from SmartApi import SmartConnect
import pyotp
from abc import ABC, abstractmethod
import time

class Broker(ABC):
    def __init__(self):
        self.connected = False

    @abstractmethod
    def connect(self, config):
        """Connect broker"""
        pass

    @abstractmethod
    def place_order(self, symbol, qty, order_type, side, price=None, stop_loss=None, target=None):
        """Place a buy/sell order."""
        pass

    @abstractmethod
    def get_balance(self):
        """Get available balance."""
        pass

    @abstractmethod
    def get_position(self, symbol):
        """Fetch current open position for a symbol."""
        pass

    @abstractmethod
    def close_position(self, symbol):
        """Close an open position."""
        pass

    def is_connected(self):
        return self.connected
    
    @abstractmethod
    def get_candle_stick_data(self, exchange, symbol, token, timeframe, startdate, enddate):
        pass


class AngelOne(Broker):
    def __init__(self, conf):
        super().__init__()
        self.apikey = conf["api_key"]
        self.pin = conf["pin"]
        self.clientid = conf["clientId"]
        self.angletoken = conf["angletoken"]
        self.smartapi = None

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

    def get_candle_stick_data(self, exchange, symbol, token, timeframe, startdate, enddate):
        historicParam = {
        "stock": symbol,
        "exchange": exchange,
        "symboltoken": token,
        "interval": timeframe,
        "fromdate": startdate.strftime("%Y-%m-%d %H:%M"),
        "todate": enddate.strftime("%Y-%m-%d %H:%M")
        }
        while(True):
            try:
                res = self.smartapi.getCandleData(historicParam)
                return res
            except Exception as e:
                print("Warning : ",str(e))
                time.sleep(1)
                print('retrying after a pause of 1 sec ....')
                continue

            
