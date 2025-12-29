
'''I will plot the accuracy of nifty 50 prediction over a day.
''' 


# %load_ext autoreload
# %autoreload 2

from datetime import datetime, timedelta
from CandleStream import CandleStream 
import pandas as pd
from calender_utils import *
import equity.utils as utils
import equity.dataset as dataset
import pandas as pd 
import numpy as np
from dotenv import load_dotenv
load_dotenv()
import yfinance as yf
import seaborn as sns
import matplotlib.pyplot as plt

stream = CandleStream()


def get_US_view():
    df = yf.download("^IXIC", start="2025-01-01", end="2025-12-31")
    df = df.xs('^IXIC', axis=1, level=1)
    df.reset_index(inplace=True)
    df['day_change'] = (df['Close'] - df['Open'])/df['Open'] * 100
    df['change_from_lastday'] = (df['Close'] - df['Close'].shift(1))/df['Close'].shift(1) * 100
    df['day_change'] = np.where((df['day_change'] > 0) &  (df['day_change'] < 0.4), 'buy',
                                np.where((df['day_change'] < 0) &  (df['day_change'] > -0.4), 'sell',
                                         np.where((df['day_change'] < -0.4), 'strong_sell',
                                                  np.where((df['day_change'] > 0.4), 'strong_buy','sideways'))))

    df['change_from_lastday'] = np.where((df['change_from_lastday'] > 0) &  (df['change_from_lastday'] < 0.4), 'buy',
                                np.where((df['change_from_lastday'] < 0) &  (df['change_from_lastday'] > -0.4), 'sell',
                                         np.where((df['change_from_lastday'] < -0.4), 'strong_sell',
                                                  np.where((df['change_from_lastday'] > 0.4), 'strong_buy','sideways'))))

    df = df[['Date', 'day_change', 'change_from_lastday']]
    df['Date'] = pd.to_datetime(df['Date']).dt.date
    df.columns = ['US_' + col  if col != 'Date' else col for col in df.columns]
    return df

def get_IN_view():
    exchange = 'NSE'
    start_date = datetime(2025, 1, 1, 9, 10)
    end_date = datetime(2026, 1, 1, 15, 30)
    interval = "1d"
    index = 'Nifty 50'
    token = utils.get_token(exchange, index)
    df = dataset.get_data(stream, 'NSE', index, token, start_date, end_date, interval)
    df['day_change'] = (df['close'] - df['open'])/df['open'] * 100
    df['change_from_lastday'] = (df['close'] - df['close'].shift(1))/df['close'].shift(1) * 100
    df['day_change'] = np.where((df['day_change'] > 0) &  (df['day_change'] < 0.4), 'buy',
                                np.where((df['day_change'] < 0) &  (df['day_change'] > -0.4), 'sell',
                                         np.where((df['day_change'] < -0.4), 'strong_sell',
                                                  np.where((df['day_change'] > 0.4), 'strong_buy','sideways'))))

    df['change_from_lastday'] = np.where((df['change_from_lastday'] > 0) &  (df['change_from_lastday'] < 0.4), 'buy',
                                np.where((df['change_from_lastday'] < 0) &  (df['change_from_lastday'] > -0.4), 'sell',
                                         np.where((df['change_from_lastday'] < -0.4), 'strong_sell',
                                                  np.where((df['change_from_lastday'] > 0.4), 'strong_buy','sideways'))))
    df['Date'] = df['timestamp'].dt.date
    df = df[['Date', 'day_change', 'change_from_lastday']]
    df.columns = ['IN_' + col  if col != 'Date' else col for col in df.columns]
    return df

def plot_correlation_matrix(df, pcrange):
    us_cols = ['US_day_change', 'US_change_from_lastday']
    in_cols = ['IN_day_change', 'IN_change_from_lastday']
    corrdf = df[us_cols + in_cols].corr().loc[us_cols, in_cols]
    sns.heatmap(corrdf, annot=True, cmap='coolwarm', annot_kws={"size":8})
    plt.xticks(rotation=0, ha="right")
    plt.yticks(rotation=0)
    plt.title(f' PCR range {pcrange}')
    plt.show()

us_df = get_US_view()
us_df['US_day_change'] = us_df['US_day_change'].shift(1)
us_df['US_change_from_lastday'] = us_df['US_change_from_lastday'].shift(1)
in_df = get_IN_view()
df = pd.merge(us_df, in_df, on='Date', how='left')
# df = df[df['US_change_from_lastday'] < -0.5]
# df.drop(['Date'], axis=1, inplace=True)
print(df.tail(40)[['Date', 'US_change_from_lastday', 'IN_day_change']])

# for pcrange in [(-3, -1), (-1, -0.5), (-0.5,0), (0, 0.5), (0.5, 1), (1, 3)]:
#     filtered_df = df[(df['US_day_change'] >= pcrange[0]) & (df['US_day_change'] < pcrange[1])]
#     print(filtered_df)
#     print(f"Correlation matrix for PCR range {pcrange}:")
#     plot_correlation_matrix(filtered_df.copy(), pcrange)


# from alpha_vantage.timeseries import TimeSerie

# # Replace with your own API key
# ts = TimeSeries(key=ALPHA_VANTAGE_KEY, output_format='pandas')

# data, meta_data = ts.get_daily(symbol="^IXIC", outputsize='full')
# print(data.head())

## do negative analysis 


# conclusion
"""
if us -> negative (-3, -1) then indian market will close  below lastday
"""