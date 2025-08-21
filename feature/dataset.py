import sys
import os
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)


from datetime import datetime, timedelta
from indicators import Indicators
import pandas as pd 

def build_data(stream, exchange, symbol, token, freq, train_date, lookbackdays):
    df = stream.fetch_data(exchange, symbol, token, train_date - timedelta(days=lookbackdays), train_date)
    df = Indicators.resample(df, freq)
    df = df.dropna()
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['time'] = df['timestamp'].dt.strftime('%H:%M')
    df['date'] = df['timestamp'].dt.date
    daily_close = df.groupby('date')['close'].last()
    df['day_close'] = df['date'].map(daily_close)
    df['condition'] = (df['time'] < '12:00') & (df['time'] > '09:40')
    df['buy'] = (df['close'] > df['high'].shift(1)) & (df['condition'])
    df['sell'] = (df['close'] < df['low'].shift(1)) & (df['condition']) 
    df['pct_change'] = (df['close'].pct_change() * 100).round(5)
    return df


def train_data(stream, exchange, symbol, token, freq, train_date, nfeatures, lookbackdays = 100):
    df = build_data(stream, exchange, symbol, token, freq, train_date, lookbackdays)
    df.reset_index(inplace = True, drop = True)
    features = []
    labels = []
    df = df[df['date'] < train_date.date()]    
    df.reset_index(inplace = True, drop = True)
    for i , row in df.iterrows():
        if i <= nfeatures:
            continue
        if row['buy']:
            feature_row = df.iloc[max(0, i-nfeatures):i+1]['pct_change'].tolist()
            feature_row.append(1)
            features.append(feature_row)
            labels.append(round((row['day_close'] - row['close'])/(row['close'])*100,5))

        if row['sell']:
            feature_row = df.iloc[max(0, i-nfeatures):i+1]['pct_change'].tolist()
            feature_row.append(0)
            features.append(feature_row)
            labels.append(round((row['close'] - row['day_close'])/(row['close'])*100,5))   
    df_model = pd.DataFrame(features)
    column_names = [f"pct_change_{i}" for i in range(len(features[0])-1)] + ["signal"]
    df_model.columns = column_names
    df_model["label"] = labels

    return features, labels         

from CandleStream import CandleStream 
from datetime import datetime, timedelta
stream = CandleStream()
features, labels = train_data(stream, 'NSE', 'TCS', 11536, "15min", datetime.today() - timedelta(1), 50, lookbackdays = 100)
print(features, labels)

##idea is to train for close candle 