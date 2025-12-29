import websocket
import hashlib
import hmac
import json
import time
import threading
from datetime import datetime
import os
from dotenv import load_dotenv
from crypto.src.logger_config import get_logger
logger = get_logger(__name__)

class DeltaWebSocketClient:
    def __init__(self, testnet=False):
        self.api_key =  os.getenv('API_KEY')
        self.api_secret = os.getenv('API_SECRET')
        if not self.api_key or not self.api_secret:
            logger.critical(f"Missing api key : {self.api_key} and missing api secret: {self.api_secret}")
            os.exit()

        if testnet:
            self.websocket_url = "wss://testnet-socket.delta.exchange"  # Update with correct testnet URL
        else:
            self.websocket_url = "wss://socket.india.delta.exchange"
        
        self.ws = None
        self.is_authenticated = False
        self.reconnect_interval = 5
        self.max_reconnect_attempts = 10
        self.reconnect_attempts = 0
        
        # Track orders and positions
        self.orders = {}
        self.positions = {}
        self.liveticker = {}
        self.live_pnl = {}
        
    def generate_signature(self, secret, message):
        """Generate HMAC SHA256 signature for authentication"""
        message = bytes(message, 'utf-8')
        secret = bytes(secret, 'utf-8')
        hash_obj = hmac.new(secret, message, hashlib.sha256)
        return hash_obj.hexdigest()
    
    def send_authentication(self):
        """Send authentication message to WebSocket"""
        method = 'GET'
        timestamp = str(int(time.time()))
        path = '/live'
        signature_data = method + timestamp + path
        signature = self.generate_signature(self.api_secret, signature_data)
        
        auth_message = {
            "type": "auth",
            "payload": {
                "api-key": self.api_key,
                "signature": signature,
                "timestamp": timestamp
            }
        }
        
        logger.info(f"[{self.get_timestamp()}] Sending authentication...")
        self.ws.send(json.dumps(auth_message))
    
    def subscribe_to_channels(self):
        """Subscribe to order updates and position updates"""
        subscription_message = {
            "type": "subscribe",
            "payload": {
                "channels": [
                    {
                        "name": "orders",
                        "symbols": ["all"]  # Track all orders, filter BTC orders in handler
                    },
                    {
                        "name": "positions", 
                        "symbols": ["all"]  # Track all positions for PnL updates
                    },
                    {
                        "name": "trading_notifications",
                        "symbols": ["all"]  # Get fill notifications, liquidations, etc.
                    },
                    {
                        "name": "v2/ticker",
                        "symbols": ["BTCUSD"]
                    }
                ]
            }
        }
        
        logger.info(f"[{self.get_timestamp()}] Subscribing to channels...")
        self.ws.send(json.dumps(subscription_message))
    
    def get_timestamp(self):
        """Get formatted timestamp for logging"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def is_btc_related(self, symbol):
        """Check if symbol is BTC related"""
        btc_symbols = ['BTCUSD', 'BTCUSDT', 'BTC', 'XBTUSD']
        return any(btc in symbol.upper() for btc in btc_symbols)
    
    def update_orders_state(self, currorder):
        currorderid = currorder['id']
        if self.orders.get(currorderid) is  None:
            logger.info(f"Order id {currorderid} is not present in {list(self.orders.keys())} So creating new one")
            self.orders[currorderid] = currorder
        else:
            del self.orders[currorderid]

    def handle_ticker_data(self, data):
        symbol = data['symbol']
        mark_price = float(data['mark_price'])
        self.liveticker[symbol] = mark_price
        active_position = self.positions.get(symbol)
        if active_position is not None:
            entry = float(active_position['entry_price'])
            size =  int(active_position["size"])
            side = 'buy' if size > 0 else 'sell'
            
            self.live_pnl[symbol] = (mark_price - entry) * size 
            
    
    def handle_order_update(self, data):
        """Handle order updates and filter for BTC orders"""
        logger.info('='*50)
        if data.get('action') == 'snapshot':
            logger.info("Received initial orders state")
            data = data['result']
            for order in data:
                self.orders[order['id']] = order
        else:    
            logger.info("Received new order state")
            order = data
            self.update_orders_state(order)
            
    def handle_position_update(self, data):
        """Handle position updates for PnL tracking"""
        logger.info('='*50)
        if data.get('action') == 'snapshot':
            logger.info("Received initial orders state")
            data = data['result']
            for position in data:
                self.positions[position['product_symbol']] = position

        else:
            logger.info("Received current pnl state : ", data['result'])

    
    def handle_trading_notification(self, data):
        """Handle trading notifications (fills, liquidations, etc.)"""
        logger.info('='*50)
        logger.info("Trading Notifications")
        logger.info("Notifications : ", data)
    
    def on_message(self, ws, message):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(message)
            message_type = data.get('type', 'unknown')
            
            if message_type == 'success' and data.get('message') == 'Authenticated':
                logger.info(f"[{self.get_timestamp()}] Authentication successful!")
                self.is_authenticated = True
                self.subscribe_to_channels()
                
            elif message_type == 'subscriptions':
                logger.info(f"[{self.get_timestamp()}]  Subscribed to channels successfully!")
                logger.info("Now tracking BTC orders and PnL updates...")
                
            elif message_type == 'orders':
                self.handle_order_update(data)
                
            elif message_type == 'positions':
                self.handle_position_update(data)
                
            elif message_type == 'trading_notifications':
                self.handle_trading_notification(data)

            elif message_type == 'v2/ticker':
                self.handle_ticker_data(data)
                
            elif message_type == 'error':
                logger.info(f"[{self.get_timestamp()}] ❌ Error: {data}")
                
            else:
                # Uncomment to see all other message types
                logger.info(f"[{self.get_timestamp()}] Other message: {message_type}")
                logger.info(data)
                pass
                
        except json.JSONDecodeError as e:
            logger.info(f"[{self.get_timestamp()}] JSON decode error: {e}")
        except Exception as e:
            logger.info(f"[{self.get_timestamp()}] Error processing message: {e}")
    
    def on_error(self, ws, error):
        """Handle WebSocket errors"""
        logger.info(f"[{self.get_timestamp()}]  WebSocket Error: {error}")
    
    def on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket connection close"""
        logger.info(f"[{self.get_timestamp()}]  Connection closed: {close_status_code} - {close_msg}")
        self.is_authenticated = False
        
        # Attempt to reconnect
        if self.reconnect_attempts < self.max_reconnect_attempts:
            self.reconnect_attempts += 1
            logger.info(f"[{self.get_timestamp()}] Attempting to reconnect ({self.reconnect_attempts}/{self.max_reconnect_attempts})...")
            time.sleep(self.reconnect_interval)
            self.connect()
        else:
            logger.info(f"[{self.get_timestamp()}] Max reconnection attempts reached. Stopping.")
    
    def on_open(self, ws):
        """Handle WebSocket connection open"""
        logger.info(f"[{self.get_timestamp()}]  WebSocket connection opened")
        self.reconnect_attempts = 0
        self.send_authentication()
    
    def connect(self):
        """Establish WebSocket connection"""
        try:
            logger.info(f"[{self.get_timestamp()}] Connecting to Delta Exchange WebSocket...")
            self.ws = websocket.WebSocketApp(
                self.websocket_url,
                on_message=self.on_message,
                on_error=self.on_error,
                on_close=self.on_close,
                on_open=self.on_open
            )
            
            # Run forever with automatic reconnection
            self.ws.run_forever(
                ping_interval=30,  # Send ping every 30 seconds
                ping_timeout=10    # Wait 10 seconds for pong
            )
            
        except Exception as e:
            logger.info(f"[{self.get_timestamp()}] Connection error: {e}")
    
    def start(self):
        """Start the WebSocket client in a separate thread"""
        def run_client():
            self.connect()
        
        client_thread = threading.Thread(target=run_client, daemon=True)
        client_thread.start()
        return client_thread
    
    
    def stop(self):
        """Close WebSocket connection gracefully"""
        logger.info(f"[{self.get_timestamp()}] Closing WebSocket connection...")
        if self.ws:
            try:
                self.ws.close()  # This signals run_forever() to exit
                logger.info(f"[{self.get_timestamp()}] WebSocket closed successfully.")
            except Exception as e:
                logger.error(f"[{self.get_timestamp()}] Error closing WebSocket: {e}")

        
    def get_current_orders(self):
        return self.orders
    
    def get_current_positions(self):
        return self.positions


