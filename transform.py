import utils

def returns(df, lastrows=20):
    df['returns'] = df['close'].pct_change() * 100
    df['returns'] = df['returns'].round(2)
    df['n_returns'] = None
    for i in range(lastrows, len(df)):
        # print(len(df['returns'].iloc[i-lastrows:i].tolist()))
        df.at[i, 'n_returns'] = df['returns'].iloc[i-lastrows:i].tolist()
    return df


def daily_returns(df):
    df = utils.resample(df, '1d')
    # df['daychange'] = df['close'].pct_change() * 100
    return df 

