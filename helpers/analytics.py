

def get_avg_price(mm):
    # VWAP as of now
    df = mm.get_histo()
    if not df.empty:
        df['prod'] = df['last'] * df['lastSize']
        return df['prod'].sum() / df['lastSize'].sum()
    else:
        return None

def get_vwap(mm):
    df = mm.get_histo()
    df['prod'] = df['last'] * df['lastSize']
    return  df['prod'].cumsum() / df['lastSize'].cumsum()

