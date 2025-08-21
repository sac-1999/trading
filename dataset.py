import utils
import pandas as pd

def fit_df_by_dates(df, start_date, end_date):
    start_date = pd.to_datetime(start_date)
    start_date = start_date.tz_localize("Asia/Kolkata")
    df = df[df['timestamp'] >= start_date]
    end_date = pd.to_datetime(end_date)
    end_date = end_date.tz_localize("Asia/Kolkata")
    df = df[df['timestamp'] <= end_date]
    return df

def get_data(stream, exchange, symbol, token, start_date, end_date, interval):
    df = stream.fetch_data(exchange, symbol, token, start_date, end_date)
    if df is None:
        raise RuntimeError(f"[Error :] Unable to fetch data for  => {exchange} {symbol} {token} {start_date} {end_date}")

    if interval == '1m' or interval == '1min':
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = fit_df_by_dates(df, start_date, end_date)
        return df
    df = utils.resample(df, interval)
    df = fit_df_by_dates(df, start_date, end_date)
    return df
    
