import pandas_ta as ta
import pandas as pd
class Indicators:
    @staticmethod
    def atr(data, feature = False, featurenumber = -1):
        if feature and featurenumber==-1:
            raise ValueError(f"[Error [atr] ] This is a feature but featurenumber{featurenumber} is not greater than -1")
        
        colname = "atr_"
        if feature:
            colname = "feature_" + str(featurenumber)
        if colname in data.columns:
            raise ValueError(f"[Error [ema] ] {colname} already exists in given dataframe")
        data[colname] = ta.atr(high=data['high'], low=data['low'], close=data['close'], length=14)
        if feature:
            data[colname] = round((data[colname] )/data['close'] * 100,2)
        return data
    
    @staticmethod
    def ema(data, length, feature = False, featurenumber = -1):
        if feature and featurenumber==-1:
            raise ValueError(f"[Error [ema] ] This is a feature but featurenumber{featurenumber} is not greater than -1")
        
        colname = "ema_" + str(length)
        if feature:
            colname = "feature_" + str(featurenumber)
        if colname in data.columns:
            raise ValueError(f"[Error [ema] ] {colname} already exists in given dataframe")
        data[colname] = ta.ema(data['close'], length)
        if feature:
            data[colname] = round((data['close'] - data[colname] )/data['close'] * 100 , 2)
        return data
    
    @staticmethod
    def supertrend(data, length, multiplier, feature = False, featurenumber = -1):
        if feature and featurenumber==-1:
            raise ValueError("[Error [supertrend]] This is a feature but {featurenumber} is not greater than -1")
        
        colname = "supertrend_" + str(length) + '_' + str(multiplier)
        if feature:
            colname = "feature_" + str(featurenumber)
        if colname in data.columns:
            raise ValueError(f"[Error [supertrend]] {colname} already exists in given dataframe")
        supertrend = ta.supertrend(high=data['high'], low=data['low'], close=data['close'], length=length, multiplier=multiplier)
        data[colname] = supertrend["SUPERT_{}_{}.0".format(length, multiplier)]
        if feature:
            data[colname] = round((data['close'] - data[colname] )/data['close'] * 100, 2)
        return data
    
    @staticmethod
    def vwap(data, feature = False, featurenumber = -1):
        if feature and featurenumber==-1:
            raise ValueError("[Error [vwap]] This is a feature but {featurenumber} is not greater than -1")
        
        colname = "vwap"
        if feature:
            colname = "feature_" + str(featurenumber)
        if colname in data.columns:
            raise ValueError(f"[Error [vwap]] {colname} already exists in given dataframe")

        data.index = pd.to_datetime(data['timestamp'])
        data[colname] = ta.vwap(data['close'], data['close'], data['close'], data['volume'])
        if feature:
            data[colname] = round((data['close'] - data[colname] )/data['close'] * 100, 2)
        data.reset_index(inplace=True, drop=True)
        return data
    
    @staticmethod
    def rsi(data, length=14, feature=False, featurenumber=-1):
        if feature and featurenumber == -1:
            raise ValueError("[Error [rsi]] featurenumber must be >= 0")
        colname = f"feature_{featurenumber}" if feature else f"rsi_{length}"
        if colname in data.columns:
            raise ValueError(f"[Error [rsi]] {colname} already exists")
        data[colname] = ta.rsi(data['close'], length)
        return data

    @staticmethod
    def macd(data, fast=12, slow=26, signal=9, feature=False, featurenumber=-1):
        if feature and featurenumber == -1:
            raise ValueError("[Error [macd]] featurenumber must be >= 0")
        macd = ta.macd(data['close'], fast=fast, slow=slow, signal=signal)
        colname = f"feature_{featurenumber}" if feature else f"macd_{fast}_{slow}_{signal}"
        if colname in data.columns:
            raise ValueError(f"[Error [macd]] {colname} already exists")
        data[colname] = macd[f"MACD_{fast}_{slow}_{signal}"]
        return data

    @staticmethod
    def bollinger_bands(data, length=20, std=2, feature=False, featurenumber=-1):
        if feature and featurenumber == -1:
            raise ValueError("[Error [bollinger]] featurenumber must be >= 0")
        bb = ta.bbands(data['close'], length=length, std=std)
        colname = f"feature_{featurenumber}" if feature else f"bb_upper_{length}_{std}"
        if colname in data.columns:
            raise ValueError(f"[Error [bollinger]] {colname} already exists")
        data[colname] = bb[f"BBU_{length}_{std}.0"]
        return data
    
    @staticmethod
    def adx(data, length=14, feature=False, featurenumber=-1):
        colname = "adx"
        if feature and featurenumber == -1:
            raise ValueError("[Error [adx]] featurenumber must be >= 0")
        if feature:
            colname = f"feature_{featurenumber}" if feature else f"adx_{length}"
        if colname in data.columns:
            raise ValueError(f"[Error [adx]] {colname} already exists")
        adx = ta.adx(data['high'], data['low'], data['close'], length=length)
        data[colname] = adx[f"ADX_{length}"]
        return data
    

    @staticmethod
    def sma(data, length, feature=False, featurenumber=-1):
        if feature and featurenumber == -1:
            raise ValueError(f"[Error [sma] ] This is a feature but featurenumber{featurenumber} is not greater than -1")
        
        colname = "sma_" + str(length)
        if feature:
            colname = "feature_" + str(featurenumber)
        if colname in data.columns:
            raise ValueError(f"[Error [sma] ] {colname} already exists in given dataframe")
        
        data[colname] = ta.sma(data['close'], length)
        if feature:
            data[colname] = round((data['close'] - data[colname] ) / data['close'] * 100 , 2)
        
        return data
    
    @staticmethod
    def stoch(data, smoothing, k=14, d=3, feature=False, featurenumber=-1):
        if feature and featurenumber == -1:
            raise ValueError(f"[Error [stoch] ] This is a feature but featurenumber {featurenumber} is not greater than -1")

        # Column names
        k_col = f"stochk_{k}_{d}"
        d_col = f"stochd_{k}_{d}"
        if feature:
            k_col = f"feature_{featurenumber}_k"
            d_col = f"feature_{featurenumber}_d"

        # Prevent duplicate
        if k_col in data.columns or d_col in data.columns:
            raise ValueError(f"[Error [stoch] ] {k_col} or {d_col} already exists in given dataframe")

        # Compute stochastic oscillator
        stoch = ta.stoch(data["high"], data["low"], data["close"], k=k, d=d, smooth_k=smoothing)
        data[k_col] = stoch.iloc[:, 0]   # %K
        data[k_col] = round(data[k_col],1)
        # data[d_col] = stoch.iloc[:, 1]   # %D

        # If using as a feature → normalize (example: difference %K - %D as %)
        # if feature:
            # data[k_col] = round((data[k_col] - data[d_col]) / 100, 2)
            # data.drop(columns=[d_col], inplace=True)

        return data

    


