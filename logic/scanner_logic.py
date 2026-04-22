import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

def nse_ticker(symbol: str) -> str:
    symbol = symbol.upper().strip().replace(".NS", "").replace(".BO", "")
    SPECIAL = {"ARE&M": "AMARARAJA.NS", "M&M": "M&M.NS", "L&T": "LT.NS"}
    return SPECIAL.get(symbol, f"{symbol}.NS")

def fetch_5y_data(ticker_ns: str):
    try:
        tk = yf.Ticker(ticker_ns)
        df = tk.history(period="5y", interval="1d")
        if df.empty:
            return None
        df.index = df.index.tz_localize(None)
        return df
    except Exception:
        return None

def compute_ichimoku(df: pd.DataFrame):
    high_9 = df['High'].rolling(window=9).max()
    low_9 = df['Low'].rolling(window=9).min()
    df['tenkan_sen'] = (high_9 + low_9) / 2

    high_26 = df['High'].rolling(window=26).max()
    low_26 = df['Low'].rolling(window=26).min()
    df['kijun_sen'] = (high_26 + low_26) / 2

    df['senkou_span_a'] = ((df['tenkan_sen'] + df['kijun_sen']) / 2).shift(26)
    
    high_52 = df['High'].rolling(window=52).max()
    low_52 = df['Low'].rolling(window=52).min()
    df['senkou_span_b'] = ((high_52 + low_52) / 2).shift(26)
    
    return df

def compute_smc(df: pd.DataFrame):
    obs = []
    fvgs = []
    for i in range(len(df)-2):
        if df['High'].iloc[i] < df['Low'].iloc[i+2]:
            fvgs.append({"type": "BULLISH FVG", "low": df['High'].iloc[i], "high": df['Low'].iloc[i+2], "date": str(df.index[i+1].date())})
        elif df['Low'].iloc[i] > df['High'].iloc[i+2]:
            fvgs.append({"type": "BEARISH FVG", "low": df['High'].iloc[i+2], "high": df['Low'].iloc[i], "date": str(df.index[i+1].date())})

    for i in range(len(df)-1):
        if df['Close'].iloc[i] < df['Open'].iloc[i]:
            if df['Close'].iloc[i+1] > df['High'].iloc[i]:
                obs.append({"type": "BULLISH OB", "low": df['Low'].iloc[i], "high": df['High'].iloc[i], "date": str(df.index[i].date())})
    
    return obs[-3:], fvgs[-3:]

def analyze_swing(df: pd.DataFrame, ticker: str):
    if df is None or len(df) < 60:
        return {"ticker": ticker, "error": "Insufficient data"}

    df = df.dropna(subset=["Close", "High", "Low"])
    if df.empty:
        return {"ticker": ticker, "error": "No valid data"}

    df = compute_ichimoku(df).copy()
    obs, fvgs = compute_smc(df)
    
    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    current_price = round(float(close.iloc[-1]), 2)
    
    sma20 = close.rolling(20).mean()
    std20 = close.rolling(20).std()
    bb_upper = sma20 + 2 * std20
    bb_lower = sma20 - 2 * std20
    
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    
    rsi_val = 0
    if not loss.empty and loss.iloc[-1] != 0:
        rsi_val = 100 - (100 / (1 + gain.iloc[-1] / loss.iloc[-1]))
    rsi = round(float(rsi_val), 2)

    ema50 = close.ewm(span=50).mean()
    ema200 = close.ewm(span=200).mean()
    curr_ema50 = round(float(ema50.iloc[-1]), 2)
    curr_ema200 = round(float(ema200.iloc[-1]), 2)
    
    tenkan = df['tenkan_sen'].iloc[-1]
    kijun = df['kijun_sen'].iloc[-1]
    span_a = df['senkou_span_a'].iloc[-1]
    span_b = df['senkou_span_b'].iloc[-1]
    
    above_cloud = bool(current_price > max(span_a, span_b))
    in_cloud = bool(min(span_a, span_b) <= current_price <= max(span_a, span_b))
    
    tr = pd.concat([high-low, (high-close.shift()).abs(), (low-close.shift()).abs()], axis=1).max(axis=1)
    atr = round(float(tr.rolling(14).mean().iloc[-1]), 2)

    strategy = "Neutral / Wait"
    entry_range = None
    targets = []
    sl = None
    in_2_sessions = False

    if obs and obs[-1]['type'] == "BULLISH OB" and current_price < obs[-1]['high'] * 1.05:
        ob = obs[-1]
        strategy = "SMC Order Block Entry"
        entry_low = ob['low']
        entry_high = ob['high']
        entry_range = f"₹{round(entry_low, 2)} - ₹{round(entry_high, 2)}"
        sl = round(entry_low - 0.5 * atr, 2)
        targets = [round(current_price + 2*atr, 2), round(current_price + 4*atr, 2), round(current_price + 7*atr, 2)]
        if current_price < entry_high * 1.02: in_2_sessions = True

    elif above_cloud and tenkan > kijun and not in_cloud:
        strategy = "Ichimoku Cloud Breakout"
        entry_low = max(span_a, span_b)
        entry_high = current_price
        entry_range = f"₹{round(entry_low, 2)} - ₹{round(entry_high, 2)}"
        sl = round(min(span_a, span_b), 2)
        targets = [round(current_price + 2.5*atr, 2), round(current_price + 5*atr, 2), round(current_price * 1.15, 2)]
        in_2_sessions = True

    elif current_price < bb_lower.iloc[-1] and rsi < 35:
        strategy = "BB Oversold Mean Reversion"
        entry_low = current_price * 0.98
        entry_high = current_price * 1.01
        entry_range = f"₹{round(entry_low, 2)} - ₹{round(entry_high, 2)}"
        sl = round(entry_low - atr, 2)
        targets = [round(sma20.iloc[-1], 2), round(bb_upper.iloc[-1], 2), round(bb_upper.iloc[-1] * 1.05, 2)]
        in_2_sessions = True

    elif current_price > curr_ema200 and rsi < 55:
        strategy = "EMA Trend Pullback"
        entry_low = curr_ema50 * 0.99
        entry_high = curr_ema50 * 1.01
        entry_range = f"₹{round(entry_low, 2)} - ₹{round(entry_high, 2)}"
        sl = round(curr_ema200 * 0.98, 2)
        targets = [round(current_price + 3*atr, 2), round(current_price + 6*atr, 2), round(current_price * 1.1, 2)]
        if current_price < entry_high * 1.04: in_2_sessions = True

    return {
        "ticker": ticker,
        "cmp": float(current_price),
        "strategy": strategy,
        "entry_range": entry_range,
        "targets": [float(t) for t in targets],
        "sl": float(sl) if sl is not None else None,
        "in_2_sessions": bool(in_2_sessions),
        "rsi": float(rsi),
        "atr": float(atr),
        "ichimoku": {"above_cloud": bool(above_cloud), "tenkan_cross": bool(tenkan > kijun)},
        "bb": {"lower": float(bb_lower.iloc[-1]), "upper": float(bb_upper.iloc[-1])},
        "smc": {"recent_ob": str(obs[-1]['type']) if obs else None}
    }

def run_scan(ticker_list):
    results = []
    for ticker in ticker_list:
        ticker_ns = nse_ticker(ticker)
        df = fetch_5y_data(ticker_ns)
        analysis = analyze_swing(df, ticker.upper())
        results.append(analysis)
    return results
