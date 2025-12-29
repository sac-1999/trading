
import os
import logging
import time
import json
import hashlib
import hmac
import requests
import urllib.parse
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Union
from enum import Enum

import pandas as pd
import pytz
from delta_rest_client import DeltaRestClient, OrderType
from logger_config import get_logger
logger = get_logger(__name__)

version = '1.0.0'

def generate_signature(secret, message):
  message = bytes(message, 'utf-8')
  secret = bytes(secret, 'utf-8')
  hash = hmac.new(secret, message, hashlib.sha256)
  return hash.hexdigest()


def get_time_stamp():
  d = datetime.datetime.utcnow()
  epoch = datetime.datetime(1970, 1, 1)
  return str(int((d - epoch).total_seconds()))

def query_string(query):
  if query == None:
    return ''
  else:
    query_strings = []
    for key, value in query.items():
      query_strings.append(key + '=' + urllib.parse.quote_plus(str(value)))
    return '?' + '&'.join(query_strings)


def parseResponse(response):
  response = response.json()
  if response['success']:
    return response['result']
  elif 'error' in response:
    raise requests.exceptions.HTTPError(response['error'])
  else:
    raise requests.exceptions.HTTPError()
  

def body_string(body):
  if body == None:
    return ''
  else:
    return json.dumps(body, separators=(',', ':'))

def raise_for_status(response):
  """Raises :class:`HTTPError`, if one occurred."""

  http_error_msg = ""
  if isinstance(response.reason, bytes):
    # We attempt to decode utf-8 first because some servers
    # choose to localize their reason strings. If the string
    # isn't utf-8, we fall back to iso-8859-1 for all other
    # encodings. (See PR #3538)
    try:
        reason = response.reason.decode("utf-8")
    except UnicodeDecodeError:
        reason = response.reason.decode("iso-8859-1")
  else:
    reason = response.reason
  if 400 <= response.status_code < 600:
      reason = response.reason + " " + str(response.text)
      http_error_msg = (
          f"{response.status_code} HTTP Error: {reason} for url: {response.url}"
      )

  if http_error_msg:
      raise requests.HTTPError(http_error_msg, response=response)

class OrderType(Enum):
    LIMIT = "limit_order"
    MARKET = "market_order"
    STOP_MARKET = "stop_market_order"
    STOP_LIMIT = "stop_limit_order"
    BRACKET = "bracket_order"

class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"

class TimeInForce(Enum):
    GTC = "gtc"  # Good Till Cancelled
    IOC = "ioc"  # Immediate or Cancel
    FOK = "fok"  # Fill or Kill

class OrderState(Enum):
    OPEN = "open"
    PENDING = "pending"
    CLOSED = "closed"
    CANCELLED = "cancelled"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"


class Broker:
    def __init__(self):
        # Initialize broker state if needed
        pass

class DeltaExchange(Broker):
    def __init__(self, testnet: bool = False):
        super().__init__()
        self.session = requests.Session()
        self.api_key = os.getenv("API_KEY")
        self.api_secret = os.getenv("API_SECRET")
        self.allproducts = None
        self.raise_for_status = True
        
        print(self.api_key)

        if not self.api_key or not self.api_secret:
            raise ValueError("API_KEY and API_SECRET must be set")

        if testnet:
            self.base_url = "https://cdn-ind.testnet.deltaex.org"
            logger.info("Using TESTNET environment")
        else:
            self.base_url = "https://api.india.delta.exchange"
            logger.info("Using PRODUCTION environment")

                    # Initialize Delta REST client
        self.client = DeltaRestClient(
            base_url= self.base_url,
            api_key=self.api_key,
            api_secret=self.api_secret
        )

        self.allassets = self.client.get_assets()

    def _init_session(self):
        session = requests.Session()
        return session

    def request(self, method, path, payload=None, query=None, auth=False, base_url=None, headers={}):
        if base_url == None:
            base_url = self.base_url
        url = '%s%s' % (base_url, path)
        res = None
        if auth:
            if self.api_key is None or self.api_secret is None:
                raise Exception('Api_key or Api_secret missing')
            timestamp = get_time_stamp()
            signature_data = method + timestamp + path + \
                query_string(query) + body_string(payload)
            signature = generate_signature(self.api_secret, signature_data)
            headers = {"Content-Type": "application/json", "api-key": self.api_key, "timestamp": timestamp,
                        "signature": signature, "User-Agent": "delta-rest-client-v" + str(version)}

            res = self.session.request(
                method, url, data=body_string(payload), params=query, timeout=(3, 6), headers=headers
            )
        else:
            non_auth_headers = {'User-Agent':'delta-rest-client-v%s'%version, 'Content-Type':'application/json'}
            res = requests.request(method, url, data=body_string(payload), params=query, timeout=(3, 6), headers=non_auth_headers)

        if self.raise_for_status:
            raise_for_status(res)
            return res


    def _load_products(self):
        """Load and cache product information"""
        if self.allproducts is None:
            try:
                self.allproducts = {}
                products = self.request("GET" , "/v2/products", auth = False)
                products = parseResponse(products)
                for product in products:
                    symbol = product.get('symbol')
                    product_id = product.get('id')
                    self.allproducts[symbol] = product_id
                    self.allproducts[product_id] = symbol

                logger.info(f"Loaded {len(self.allproducts)} products")
            except Exception as e:
                logger.error(f"Failed to load products: {e}")

    def get_product_id(self, symbol: str) -> Optional[int]:
        """Get product ID for a given symbol"""
        self._load_products()
        return self.allproducts.get(symbol)
    
    def get_symbol(self, product_id: int) -> Optional[str]:
        """Get symbol for a given product ID"""
        return self.allproducts.get(product_id)
        
    
    def place_order(self, product_symbol: str, side: str, size: int, 
                   order_type: str = "LIMIT", limit_price: str = None,
                   time_in_force: str = None, reduce_only: bool = False,
                   client_order_id: str = None) -> Dict:
        """
        Place a new order using the delta_rest_client
        
        Args:
            product_symbol: Trading symbol (e.g., "BTCUSD")
            side: "buy" or "sell"
            size: Order size (integer, no fractional values)
            order_type: "LIMIT" or "MARKET"
            limit_price: Price for limit orders
            time_in_force: Order time in force
            reduce_only: Only close positions if True
            client_order_id: Custom order ID
            
        Returns:
            Order response
        """
        try:
            product_id = self.get_product_id(product_symbol)
            if not product_id:
                return {"success": False, "error": f"Product {product_symbol} not found"}
            
            # Convert string order type to OrderType enum
            if order_type.upper() == "LIMIT":
                order_type_enum = OrderType.LIMIT
            elif order_type.upper() == "MARKET":
                order_type_enum = OrderType.MARKET
            else:
                return {"success": False, "error": f"Unsupported order type: {order_type}"}
            
            # Convert side to proper format
            trade_type = side.lower()
            
            logger.info(f"Placing {side} order for {size} {product_symbol} (ID: {product_id})")
            
            # Use the specific method signature you provided
            response = self.client.place_order(
                product_id=product_id,
                size=size,
                side=trade_type,
                limit_price=limit_price,
                time_in_force=time_in_force,
                order_type=order_type_enum
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return {"success": False, "error": str(e)}

    def get_balance(self, asset_symbol = 'USD'):
        for asset in self.allassets:
            if asset['symbol'] == asset_symbol:
                asset_info =  self.client.get_balances(asset_id=asset['id'])
                return asset_info['available_balance']
        logger.info(f"Missing asset symbol - {asset_symbol} - in all assets")

    def get_pending_orders(self):
       self.client.get_live_orders()

       
    def create_order(self, order):
        response = self.request('POST', "/v2/orders", order, auth=True)
        return parseResponse(response)

    def place_bracket_order(self, symbol : str, size : int, stopprice:int, targetprice:int):
        product_id = self.get_product_id(symbol)
        if not product_id:
            return {"success": False, "error": f"Product {symbol} not found"}
        order = {  "product_id": product_id,
                    "product_symbol": symbol,
                    "stop_loss_order": {
                                        "order_type": OrderType.MARKET.value,
                                        "stop_price": str(stopprice),
                                    },
                    "take_profit_order": {
                                        "order_type": OrderType.MARKET.value,
                                        "stop_price": str(targetprice),
                                    },
                    "bracket_stop_trigger_method": "last_traded_price"
                }
      
        response = self.request('POST', "/v2/orders/bracket", order, auth=True)
        response = response.json()
        print(response)
        return response  
    
    def modify_bracket_order(self,  symbol : str,  stopprice:int, targetprice:int):
        product_id = self.get_product_id(symbol)
        if not product_id:
            return {"success": False, "error": f"Product {symbol} not found"}
        order = {
            "id": 1058673805,
            "product_id": product_id,
            "product_symbol": symbol,
            "bracket_stop_loss_price": str(stopprice),
            "bracket_take_profit_price": "95000",
            "bracket_stop_trigger_method": "last_traded_price"
            }
        response = self.request('PUT', "/v2/orders/bracket", order, auth=True)
        response = response.json()
        print(response)
        return response   

    def _get_unix_timestamp(self, dt):
        return int(time.mktime(dt.timetuple()))


    def get_historical_data(self, symbol, interval='5m', days=1):
        end_dt = datetime.now() + timedelta(minutes=1)
        start_dt = end_dt - timedelta(days=days)

        start_unix = self._get_unix_timestamp(start_dt)
        end_unix = self._get_unix_timestamp(end_dt)

        url = 'https://api.india.delta.exchange/v2/history/candles'
        params = {
            'resolution': interval,
            'symbol': symbol,
            'start': start_unix,
            'end': end_unix
        }
        headers = {'Accept': 'application/json'}
        response = requests.get(url, params=params, headers=headers)

        if response.status_code == 200:
            data = response.json()
            df = pd.DataFrame(data['result'])
            if df.empty:
                logger.info("No data found for the given parameters.")
                return df

            df['time'] = pd.to_datetime(df['time'], unit='s',  utc=True).dt.tz_convert(pytz.timezone('Asia/Kolkata'))
            df = df[::-1]
            df.reset_index(inplace=True, drop=True)
            return df
        else:
            raise ConnectionError(f"Failed to fetch data: {response.status_code} - {response.text}")
        
    def get_historical_data_by_dates(self, symbol, interval='5m', start_date=None, end_date=None):
        start_unix = self._get_unix_timestamp(start_date)
        end_unix = self._get_unix_timestamp(end_date)

        url = 'https://api.india.delta.exchange/v2/history/candles'
        params = {
            'resolution': interval,
            'symbol': symbol,
            'start': start_unix,
            'end': end_unix
        }
        headers = {'Accept': 'application/json'}
        response = requests.get(url, params=params, headers=headers)

        if response.status_code == 200:
            data = response.json()
            df = pd.DataFrame(data['result'])
            if df.empty:
                logger.info("No data found for the given parameters.")
                return df

            df['time'] = pd.to_datetime(df['time'], unit='s',  utc=True).dt.tz_convert(pytz.timezone('Asia/Kolkata'))
            df = df[::-1]
            df.reset_index(inplace=True, drop=True)
            return df
        else:
            raise ConnectionError(f"Failed to fetch data: {response.status_code} - {response.text}")


    def get_active_positions(self, symbol):
        product_id = self.get_product_id(symbol)
        if not product_id:
            logger.critical(f"Seems like {symbol} is not a valid product is {product_id}")
            return  None
        positions = self.client.get_position(product_id)
        if positions is not None:
            price = positions['entry_price']
            size = positions['size']
            if size < 0:
                side = 'sell'
            if size > 0:
                side = 'buy'
            return (price, side)
        return None, None
    