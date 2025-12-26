import utils
import dataset
from CandleStream import CandleStream 
import requests
import json
from datetime import datetime, timedelta
import os
import time
import telegram_services
import asyncio

stream = CandleStream()

##global parameters
symbol = 'NIFTY'
expiry = None
premium_gap = 50

today_date = datetime.today() + timedelta(hours= 6)

tradefile = f"./optiontrades/{today_date.strftime('%Y-%m-%d')}.json"
if os.path.exists(tradefile):
    print("File exists.")
else:
    with open(tradefile, 'w') as f:
        json.dump({}, f, indent=4)

def download_scrip_master_v1():
    url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
    response = requests.get(url)

    if response.status_code == 200:
        scrips = response.json()
        return scrips
    else:
        raise Exception(f"Failed to fetch data: {response.status_code}")
    
def get_token_list(scrip, symbol:str) ->tuple[dict, list]:
    """ It will return all the dictionary of tokens and with list of expiry"""
    token_dict = {}
    listofexpiry = set()
    for elem in scrip:
        if elem['instrumenttype'] == 'OPTIDX' and elem['exch_seg'] == 'NFO' and elem['name'] == symbol:
            token_dict[elem['symbol']] = elem['token']
            listofexpiry.add(elem['expiry'])

    listofexpiry = list(listofexpiry)
    listofexpiry = sorted(listofexpiry)
    return token_dict, listofexpiry


scrip = download_scrip_master_v1()

def weekly_expiry(listofexpiry : list) -> datetime.date:
    """It will return the closest expiry to trade"""
    todaydate = datetime.today().date()
    converted_dates = [datetime.strptime(date, "%d%b%Y").date() for date in listofexpiry]
    maxgap = 100000
    weekly_expiry_date = None
    for date in converted_dates:
        if date >= todaydate:
            if maxgap > (date - todaydate).days:
                maxgap = (date - todaydate).days
                weekly_expiry_date = date
    weekly_expiry_date = weekly_expiry_date.strftime("%d%b%Y").upper()
    year = weekly_expiry_date[-2:]
    return weekly_expiry_date[:-4] + year

def at_the_money_premium(symbol : str, index_price : int, expiry : str) -> tuple[str, str]:
    """This will return a tuple of ce and pe premium symbols at the money."""
    index_price = int(index_price)
    rem = index_price % premium_gap
    premium_price = index_price - rem
    premium_symbol_ce = symbol + expiry + str(premium_price) + 'CE'
    premium_symbol_pe = symbol + expiry + str(premium_price + premium_gap) + 'PE'
    if rem == 0:
        premium_symbol_pe = symbol + expiry + str(premium_price) + 'PE'

    return premium_symbol_ce, premium_symbol_pe

def get_index_data_in_realtime(exchange, symbol, date, interval):
    token = utils.get_token_for_index(exchange, symbol)
    df = dataset.get_data(stream, 'NSE', symbol, token, date - timedelta(1), date, interval, offset='5min') 
    df['day'] = df['timestamp'].dt.date
    df = utils.filter_data_by_dates(df.copy(), date, date)
    return df

def get_premium_data_in_realtime(exchange, symbol,token, date, interval):
    df = dataset.get_data(stream, exchange, symbol, token, date - timedelta(1), date, interval, offset='5min') 
    df['day'] = df['timestamp'].dt.date
    df = utils.filter_data_by_dates(df.copy(), date, date)
    return df

def fit_trade_rule(df):
    df['isgoodclose'] = df['close'] > df['high'].shift(1)

    df['cond1'] = (
    (df['isgoodclose'].shift(1) == False) &
    (df['isgoodclose'].shift(2) == False) &
    (df['isgoodclose'] == True))
    df['breakout'] = (df['high'] > df['high'].shift(1)) & (df['cond1'].shift(1))
    df['entry'] = df['high'].shift(1)
    df['sl'] = df['low'].shift(1)
    print(df.tail(5))
    if df.iloc[-1]['breakout']:
        return df.iloc[-1]
    return None

token_dict, listofexpiry = get_token_list(scrip, symbol)
expiry = weekly_expiry(listofexpiry)
interval = "2min"
exchange = 'NSE'

while(True):
    try:
        indexdf = get_index_data_in_realtime(exchange, symbol, today_date, interval)
        lasttime = indexdf.iloc[-1]['timestamp']
        with open(tradefile, 'r') as f:
            trade_data = json.load(f)
        
        if trade_data.get(str(lasttime)) is not None:
            print("XXXXXXXXXXXXXXXXXXX trades already placed for this time periods", str(lasttime))
            continue
        else:
            print("/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/-/- Looking for trades ", str(lasttime))


        currprice = int(indexdf.iloc[-1]['close'])
        premium_symbol_ce, premium_symbol_pe = at_the_money_premium(symbol, currprice, expiry)
        premium_symbol_ce_token, premium_symbol_pe_token =  token_dict[premium_symbol_ce], token_dict[premium_symbol_pe]
        premium_symbol_ce_token, premium_symbol_pe_token

        buy_df = get_premium_data_in_realtime('NFO', premium_symbol_ce, premium_symbol_ce_token, today_date, interval)
        sell_df = get_premium_data_in_realtime('NFO', premium_symbol_pe, premium_symbol_pe_token, today_date, interval)

        buy_df = fit_trade_rule(buy_df)
        sell_df = fit_trade_rule(sell_df)
        print('--------------------------------------------------------')
        # print(sell_df)

        if buy_df is not None:
            currtrade = {'entry' : buy_df['entry'], 'sl' : buy_df['sl'], 'symbol' : premium_symbol_ce}
            trade_data[str(buy_df['timestamp'])] = currtrade
                    
            message = (
                f"📢 New Trade Alert!\n\n"
                f"🔹 {currtrade['symbol']}`\n"
                f"💰 Entry : `{currtrade['entry']}`\n"
                f"🛡️ Stop Loss : `{currtrade['sl']}`\n"
                f"⏰ Time : `{str(buy_df['timestamp'])[11:16]}`"
            )
            asyncio.run(telegram_services.send_trade(message))

        elif sell_df is not None:
            currtrade = {'entry' : sell_df['entry'], 'sl' : sell_df['sl'], 'symbol' : premium_symbol_pe}
            trade_data[str(sell_df['timestamp'])] = currtrade
            
            message = (
                f"📢 New Trade Alert!\n\n"
                f"🔹 {currtrade['symbol']}`\n"
                f"💰 Entry : `{currtrade['entry']}`\n"
                f"🛡️ Stop Loss : `{currtrade['sl']}`\n"
                f"⏰ Time : `{str(buy_df['timestamp'])[11:16]}`"
            )

            asyncio.run(telegram_services.send_trade(message))

        
        if buy_df is not None or sell_df is not None:
            with open(tradefile, 'w') as f:
                json.dump(trade_data, f, indent=4)
        
        time.sleep(1)
    except Exception as e:
        print('Exception occured', e)
        time.sleep(5)

