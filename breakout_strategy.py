# %load_ext autoreload
# %autoreload 2

from datetime import datetime, timedelta
from CandleStream import CandleStream 
import pandas as pd
from calender_utils import *
import utils
import dataset
import strategy

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.dates as mdates
stream = CandleStream()


exchange = 'NSE'
start_date = datetime(2024, 1, 13, 9, 10)
end_date = datetime(2025, 7, 20, 9, 10)
interval = "10min"
bookrr = 2
all_results = []
is_live = False
save_image = False
risk = 1000
rrlist = [1.5, 2, 2.5]
tax_pct = 0.1

# changedf = None
# for symbol in pd.read_csv('ind_nifty50list.csv')['Symbol']:
#     try:
#         token = utils.get_token(exchange, symbol + '-EQ')
#         df = dataset.get_data(stream, 'NSE', symbol, token, start_date, end_date, interval)
#         df['day'] = df['timestamp'].dt.date
#         daydf = utils.resample(df.copy(), '1d')
#         daydf['day'] = daydf['timestamp'].dt.date
#         # daydf['day'] = daydf['day'].shift(-1)
#         daydf = daydf.drop(['timestamp'], axis = 1)
#         daydf.rename(columns  = {'open' : 'previous_day_open',
#             'close' : 'previous_day_close',
#             'low' : 'previous_day_low',
#             'high' : 'previous_day_high',
#             'volume' : 'previous_day_volume'}, inplace = True)

#         daydf = daydf[['day', 'previous_day_open']]
#         df = pd.merge(df, daydf, on = 'day', how = 'left')
#         df['change_pct'] = round((df['close'] - df['previous_day_open']) / df['previous_day_open'] * 100 , 2)
#         df = df[['timestamp', 'change_pct']] 
#         df.rename(columns = {'change_pct' : symbol}, inplace=True)
#         if changedf is None:
#             changedf = df.copy()

#         else:
#             changedf = pd.merge(changedf, df, on = 'timestamp', how = 'left')
        
#     except Exception as e:
#         print('Error : ', e)

        
# changedf = changedf.dropna()
# changedf.reset_index(inplace=True, drop = True)
changedf_dict = {}
# for i, row in changedf.iterrows():
#     row_dict = row.drop('timestamp').to_dict() 
#     row_dict = dict(sorted(row_dict.items(), key=lambda item: item[1], reverse=True))
#     changedf_dict[row['timestamp']] = row_dict
    
# print(changedf_dict)

while(True):
    for symbol in pd.read_csv('ind_nifty50list.csv')['Symbol']:
        if 'adani' in symbol.lower():
            continue

        # if 'TCS' != symbol:
        #     continue
        try:
            token = utils.get_token(exchange, symbol + '-EQ')
            orgdf = dataset.get_data(stream, 'NSE', symbol, token, start_date, end_date, interval)
            mystrategy = strategy.VWAP_by_YatinKoodi(orgdf.copy(), 'buy', window = 3, ema_list = [8, 21, 50], symbol = symbol, save_trade = save_image, live = is_live, change_dict = changedf_dict)
            results = mystrategy.run()
            all_results.extend(results)
            mystrategy = strategy.VWAP_by_YatinKoodi(orgdf.copy(), 'sell', window = 3, ema_list = [8, 21, 50], symbol = symbol, save_trade = save_image, live = is_live, change_dict = changedf_dict)
            results = mystrategy.run()
            all_results.extend(results)
            # break
        except Exception as e:
            print('Error : ', e)
    if is_live == False:
        break
    

for rr in rrlist:
    print('-'*30, rr, '-'*30)
    df = pd.DataFrame(all_results)
    print(all_results)
    print(df)
    df.to_csv("allresults.csv",index=False)
    df['goodtrade'] = np.where(df['goodtrade'] > rr, rr, -1)
    print(f"Accuracy of my system is : {round(len(df[df['goodtrade']>=rr])/len(df),2)} %")
    print(f"Number od trades taken : {len(df)}")
    df['day'] = pd.to_datetime(df['tradetime']).dt.date
    df = df.sort_values(by='tradetime').reset_index(drop=True)
    df['tax'] = risk * tax_pct
    df['goodtrade'] = df['goodtrade'] * risk - df['tax']
    df['goodtrade'] = df['goodtrade'].cumsum()
    df['day'] = pd.to_datetime(df['day'])
    plt.figure(figsize=(12, 6))
    plt.plot(df['day'], df['goodtrade'], marker='o', color='darkorange')
    plt.title('Cumulative Goodtrade Over Time')
    plt.xlabel('Date')
    plt.ylabel('Profit (₹)')
    plt.gca().xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.MO, interval=1))
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d-%b'))

    plt.xticks(rotation=45)
    plt.grid(True)
    plt.tight_layout()
    plt.show()