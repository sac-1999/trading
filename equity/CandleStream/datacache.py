import os
import sys
import pandas as pd
from dotenv import load_dotenv
from functools import wraps
import hashlib
import pickle
from datetime import datetime, timedelta

# === Paths ===
from appdirs import user_cache_dir

cache_dir = user_cache_dir("candlestream")
os.makedirs(cache_dir, exist_ok=True)

# === Config Loader ===
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
        },
        "TELEGRAM": {
            "token": os.getenv("TELEGRAM_TOKEN"),
            "chatid": os.getenv("TELEGRAM_CHATID"),
        }
    }

# === FileDict ===
class FileDict:
    def __init__(self, path):
        self.path = path
        os.makedirs(path, exist_ok=True)

    def _get_file_path(self, func_key, arg_hash):
        filename = f"{func_key}_{arg_hash}.pkl"
        return os.path.join(self.path, filename)

    def get(self, func_key, arg_hash):
        file_path = self._get_file_path(func_key, arg_hash)
        if not os.path.exists(file_path):
            raise KeyError(f"No cache found for key: {func_key} with hash: {arg_hash}")
        with open(file_path, 'rb') as file:
            return pickle.load(file)

    def set(self, func_key, arg_hash, value):
        file_path = self._get_file_path(func_key, arg_hash)
        with open(file_path, 'wb') as file:
            pickle.dump(value, file)

    def contains(self, func_key, arg_hash):
        return os.path.exists(self._get_file_path(func_key, arg_hash))

# === Helpers ===
def month_end_day(scanday):
    if scanday.month == 12:
        next_month = datetime(scanday.year + 1, 1, 1)
    else:
        next_month = datetime(scanday.year, scanday.month + 1, 1)
    return next_month - timedelta(seconds=1)

def is_same_month(scanday):
    print(scanday)
    today = datetime.today()
    return scanday.year == today.year and scanday.month == today.month

def is_same_day(scanday):
    return scanday.date() == datetime.today().date()

def filter_by_day(df, day):
    df = df[df['timestamp'].apply(lambda x: x[:10]) == day.strftime('%Y-%m-%d')]
    df.reset_index(drop=True, inplace=True)
    return df

# === Decorator ===
def load_or_save_dataframe(subdir=None):
    file_cache = FileDict(os.path.join(cache_dir, subdir))

    def decorator(func):
        @wraps(func)
        def wrapper(self, exchange, symbol, token, scanday, *args, **kwargs):
            print(exchange, symbol, token, scanday)
            if is_same_month(scanday):
                return func(self, exchange, symbol, token, scanday, *args, **kwargs)

            scanday = month_end_day(scanday)
            func_key = f"{func.__module__}.{func.__name__}"
            arg_key = f"{symbol}:{scanday.date()}:{args}:{kwargs}"
            arg_hash = f"{symbol}_{scanday.date()}_" + hashlib.md5(arg_key.encode()).hexdigest()

            if file_cache.contains(func_key, arg_hash):
                return file_cache.get(func_key, arg_hash)

            df = func(self, exchange, symbol, token, scanday, *args, **kwargs)
            if df is not None:
                file_cache.set(func_key, arg_hash, df)
            return df

        return wrapper
    return decorator

# === Broker Setup and Sync ===
class CandleStream:
    def __init__(self):
        config = load_config()
        from .broker import AngelOne
        self.broker = AngelOne(config['BROKERCONFIG'])
        if not self.broker.connect():
            raise ConnectionError("Unable to connect to broker.")

    @load_or_save_dataframe('data')
    def sync(self, exchange, symbol, token, scanday):
        startday = datetime(scanday.year, scanday.month, 1)
        endday = month_end_day(scanday)
        print(f"Syncing for {symbol} from {startday} to {endday}")

        response = self.broker.get_candle_stick_data(exchange, symbol, token, 'ONE_MINUTE', startday, endday)
        if response.get('data'):
            data = pd.DataFrame(response['data'], columns=["timestamp", "open", "high", "low", "close", "volume"])
            return data[["timestamp", "open", "high", "low", "close", "volume"]]
        return None

    def fetch_data(self, exchange, symbol, token, startdate, enddate):
        if startdate > enddate:
            raise ValueError(f"Invalid date range: {startdate} > {enddate}")

        enddate = month_end_day(enddate)
        dfs = []
        while startdate <= enddate:
            scanday = month_end_day(startdate)
            df = self.sync(exchange, symbol, token, scanday)
            if df is not None:
                dfs.append(df)
            startdate = scanday + timedelta(1)

        if dfs:
            return pd.concat(dfs).reset_index(drop=True)
        return None
