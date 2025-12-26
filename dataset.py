import utils
import pandas as pd
import time

def fit_df_by_dates(df, start_date, end_date):
    start_date = pd.to_datetime(start_date)
    start_date = start_date.tz_localize("Asia/Kolkata")
    df = df[df['timestamp'] >= start_date]
    end_date = pd.to_datetime(end_date)
    end_date = end_date.tz_localize("Asia/Kolkata")
    df = df[df['timestamp'] <= end_date]
    return df

def get_data(stream, exchange, symbol, token, start_date, end_date, interval, offset = '0min'):
    maxretry = 5
    retrycount = 0
    while(retrycount < maxretry):
        df = stream.fetch_data(exchange, symbol, token, start_date, end_date)
        if df is None:
            print(f"[Error :] Unable to fetch data for  => {exchange} {symbol} {token} {start_date} {end_date}",   "retrying ***********in 1 sec")
            retrycount += 1
            time.sleep(2)
            continue

        if interval == '1m' or interval == '1min':
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = fit_df_by_dates(df, start_date, end_date)
            df['time'] = df['timestamp'].dt.time
            df['date'] = df['timestamp'].dt.date
            return df
        df = utils.resample(df, interval, offset)
        df = fit_df_by_dates(df, start_date, end_date)
        df['time'] = df['timestamp'].dt.time
        df['date'] = df['timestamp'].dt.date
        return df
    
