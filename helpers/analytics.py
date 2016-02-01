import pandas as pd

def get_avg_price(mm):
    # VWAP as of now
    df = mm.get_histo()
    if not df.empty:
        df['prod'] = df['last'] * df['lastSize']
        return df['prod'].sum() / df['lastSize'].sum()
    else:
        return pd.DataFrame()

def get_vwap(mm):
    df = mm.get_histo()
    if not df.empty:
        df['prod'] = df['last'] * df['lastSize']
        df = df.resample('10S', how='sum')
        return  df['prod'].cumsum() / df['lastSize'].cumsum()
    else:
        return pd.DataFrame()

