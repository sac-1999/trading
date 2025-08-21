from indicators import Indicators
import pandas as pd
from datetime import datetime

class TradeFuture:
    def __init__(self, df, tradetype, entrycol, atr_sl_multiplier): 
        self.df = df
        self.tradetype = tradetype
        self.entrycol = entrycol
        self.atr_sl_multiplier = atr_sl_multiplier

    def update_sl(self):
        ## for buy side entry col should be close or high
        ## for sell side entry col should be close or low
        df = self.df.copy()
        df = Indicators.atr(df)
        df['sl'] = -1.0
        for i, row in df.iterrows():
            if row['istrade']:
                if self.tradetype == 'buy':
                    df.loc[i, 'sl'] = min(row['low'], row[self.entrycol] - self.atr_sl_multiplier * row['atr'])
                elif self.tradetype == 'sell':
                    df.loc[i, 'sl'] = max(row['high'], row[self.entrycol] + self.atr_sl_multiplier * row['atr'])
        self.df = df

    def check_profit_for_day(self, df, date, entry, sl, entrytime, dayendtime):
        # Ensure time types are correct
        if isinstance(entrytime, str):
            entrytime = datetime.strptime(entrytime, '%H:%M:%S').time()

        if isinstance(dayendtime, pd.Timestamp):
            dayendtime = dayendtime.time()
        elif isinstance(dayendtime, str):
            dayendtime = datetime.strptime(dayendtime, '%H:%M:%S').time()

        # Filter by date and time range
        df = df[(df['date'] == date) & (df['time'] >= entrytime) & (df['time'] <= dayendtime)]

        maxrr = 0
        for _, row in df.iterrows():
            if self.tradetype == 'buy':
                if row['low'] < sl:
                    break
                rr = (row['high'] - entry) / (entry - sl)
                maxrr = max(maxrr, rr)
            elif self.tradetype == 'sell':
                if row['high'] > sl:
                    break
                rr = (entry - row['low']) / (sl - entry)
                maxrr = max(maxrr, rr)

        return round(maxrr, 2)

    def update_achieved_rr(self):        
        df = self.df.copy()
        if 'sl' not in df.columns:
            raise ValueError("[Error] Please run sl section first to populate sl column")

        df['date'] = pd.to_datetime(df['timestamp']).dt.date
        df['time'] = pd.to_datetime(df['timestamp']).dt.time

        df['rr'] = 0.0
        for i, row in df.iterrows():
            if row['istrade']:
                rr = self.check_profit_for_day(
                    df.copy(),
                    row['date'],
                    row[self.entrycol],
                    row['sl'],
                    row['time'],
                    datetime.strptime('15:00:00', '%H:%M:%S').time()
                )
                df.loc[i, 'rr'] = rr
        self.df = df

    def execute(self):
        self.update_sl()
        self.update_achieved_rr()
        self.df = self.df.drop(columns = ['date', 'time'])
        return self.df