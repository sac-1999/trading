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

print(stream.broker.is_connected())

exchange = 'NSE'
start_date = datetime(2025, 8, 1, 9, 10)
end_date = datetime(2025, 8, 20, 9, 10)
interval = "10min"
bookrr = 2
all_results = []
is_live = True
save_image = True
risk = 1000
rrlist = [1.5, 2]
tax_pct = 0.1

while(True):
    for symbol in pd.read_csv('ind_nifty500list.csv')['Symbol']:
        try:
            token = utils.get_token(exchange, symbol + '-EQ')
            orgdf = dataset.get_data(stream, 'NSE', symbol, token, start_date, end_date, interval)
            mystrategy = strategy.Yatin_plus_ayushi(orgdf.copy(), 'buy', window = 3, ema_list = [8, 21, 50, 100], symbol = symbol, save_trade = save_image, live = is_live)
            results = mystrategy.run()
            all_results.extend(results)
            mystrategy = strategy.Yatin_plus_ayushi(orgdf.copy(), 'sell', window = 3, ema_list = [8, 21, 50, 100], symbol = symbol, save_trade = save_image, live = is_live)
            results = mystrategy.run()
            all_results.extend(results)
            # break
        except Exception as e:
            print('Error : ', e)
    if is_live == False:
        break

if len(all_results)!=0:
    for rr in rrlist:
        print('-'*30, rr, '-'*30)
        df = pd.DataFrame(all_results)
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

