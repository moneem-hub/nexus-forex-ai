import pandas as pd


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df['Body']  = abs(df['Close'] - df['Open'])
    df['Range'] = df['High'] - df['Low']

    delta = df['Close'].diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = delta.clip(upper=0).abs().rolling(14).mean()
    df['RSI'] = 100 - (100 / (1 + gain / (loss + 1e-9)))

    exp1 = df['Close'].ewm(span=12).mean()
    exp2 = df['Close'].ewm(span=26).mean()
    df['MACD']        = exp1 - exp2
    df['MACD_Signal'] = df['MACD'].ewm(span=9).mean()

    bb_mid = df['Close'].rolling(20).mean()
    bb_std = df['Close'].rolling(20).std()
    bb_up  = bb_mid + 2 * bb_std
    bb_lo  = bb_mid - 2 * bb_std
    df['BB_Position'] = (df['Close'] - bb_lo) / (bb_up - bb_lo + 1e-9)

    tr = pd.concat([
        (df['High'] - df['Low']),
        (df['High'] - df['Close'].shift()).abs(),
        (df['Low']  - df['Close'].shift()).abs(),
    ], axis=1).max(axis=1)
    df['ATR'] = tr.rolling(14).mean()

    df['Price_Change'] = df['Close'].pct_change()
    df['Volatility']   = df['Price_Change'].rolling(10).std()
    df['Close_Lag_1']  = df['Close'].shift(1)
    df['Close_Lag_2']  = df['Close'].shift(2)
    df['Return_Lag_1'] = df['Close'].pct_change(1).shift(1)
    df['SMA_Open']     = df['Open'].rolling(9).mean()
    df['SMA_Low']      = df['Low'].rolling(9).mean()

    df.dropna(inplace=True)
    return df
