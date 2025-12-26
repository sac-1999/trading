class Strategy:
    @staticmethod
    def time_5_ema_11(df, ema):
        orgcols = list(df.columns)
        df['buyforce'] = (df['close'] > df['high'].shift(1)) & (df['close'] > df[ema]) & (df['open'] < df[ema])
        df['trading_below_ema'] = (df['close'] < df[ema]) & (df['close'] < df['high'].shift(1))
        df['buy'] = (df['high'] > df['high'].shift(1)) & (df['buyforce'].shift(1)) & (df['trading_below_ema'].shift(2) | df['trading_below_ema'].shift(3))
        df['entry'] = df['high'].shift(1)
        df['sl'] = df['low'].shift(1) - abs((df['low'].shift(1) - df['low'].shift(2)/2))


        df['sellforce'] = (df['close'] < df['low'].shift(1)) & (df['close'] < df[ema]) & (df['open'] > df[ema])
        df['trading_above_ema'] = (df['close'] > df[ema]) & (df['close'] > df['low'].shift(1))
        df['sell'] = (df['low'] < df['low'].shift(1)) & (df['sellforce']) & (df['trading_above_ema'].shift(2) | df['trading_above_ema'].shift(3))
        df['entry'] = df['low'].shift(1)
        df['sl'] = df['high'].shift(1) + abs((df['high'].shift(1) - df['high'].shift(2)/2))

        orgcols.append('buy')
        orgcols.append('sell')
        orgcols.append('entry')
        orgcols.append('sl')
        df = df[orgcols]
        return df
