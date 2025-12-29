import time
from utils import *
from dataingestion import  BTCDataLoader
from broker import DeltaExchange
import schedule
from dotenv import load_dotenv
load_dotenv()

SYMBOL = 'BTCUSD'

broker = DeltaExchange()
databaseloader = BTCDataLoader()
    
def sync():
    df = load_data(broker, SYMBOL,datetime.today() - timedelta(hours=1), datetime.today())
    if df is not None and len(df)>0:
        list_of_jsons = df.to_dict(orient='records')
        databaseloader.insert_candles(list_of_jsons)
        print(df.iloc[-1])


schedule.every(30).seconds.do(sync)

while True:
    schedule.run_pending()
    time.sleep(1)