
import yfinance as yf
import pandas as pd
import numpy as np
import telegram
import datetime

# 환경 변수 또는 직접 입력
BOT_TOKEN = "여기에_봇_토큰_입력"
CHAT_ID = "여기에_CHAT_ID_입력"

bot = telegram.Bot(token=BOT_TOKEN)

def calc_adx_vector(df, period=14):
    df['High_prev'] = df['High'].shift(1)
    df['Low_prev'] = df['Low'].shift(1)
    df['Close_prev'] = df['Close'].shift(1)
    df['TR1'] = df['High'] - df['Low']
    df['TR2'] = (df['High'] - df['Close_prev']).abs()
    df['TR3'] = (df['Low'] - df['Close_prev']).abs()
    df['TR'] = df[['TR1', 'TR2', 'TR3']].max(axis=1)
    df['up_move'] = df['High'] - df['High_prev']
    df['down_move'] = df['Low_prev'] - df['Low']
    df['+DM'] = np.where((df['up_move'] > df['down_move']) & (df['up_move'] > 0), df['up_move'], 0)
    df['-DM'] = np.where((df['down_move'] > df['up_move']) & (df['down_move'] > 0), df['down_move'], 0)
    df['TR_sum'] = df['TR'].rolling(window=period).sum()
    df['+DM_sum'] = df['+DM'].rolling(window=period).sum()
    df['-DM_sum'] = df['-DM'].rolling(window=period).sum()
    df['DI+'] = 100 * (df['+DM_sum'] / df['TR_sum'])
    df['DI-'] = 100 * (df['-DM_sum'] / df['TR_sum'])
    df['DX'] = 100 * ((df['DI+'] - df['DI-']).abs() / (df['DI+'] + df['DI-']))
    df['ADX'] = df['DX'].rolling(window=period).mean()
    df.drop(columns=['High_prev','Low_prev','Close_prev','TR1','TR2','TR3',
                     'up_move','down_move','+DM','-DM','TR_sum','+DM_sum','-DM_sum','DX'], inplace=True)
    return df

def send_signals():
    symbols = ["TSLA", "AAPL", "NVDA", "META", "GOOGL", "MSFT", "AMZN"]
    for symbol in symbols:
        try:
            df = yf.download(symbol, period="6mo", interval="1d", progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(1)
            df = calc_adx_vector(df)
            df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
            df['EMA60'] = df['Close'].ewm(span=60, adjust=False).mean()
            df['Buy_Signal'] = (df['EMA20'] > df['EMA60']) & (df['EMA20'].shift(1) <= df['EMA60'].shift(1)) & (df['ADX'] >= 20) & (df['DI+'] > df['DI-'])
            df['Sell_Signal'] = (df['EMA20'] < df['EMA60']) & (df['EMA20'].shift(1) >= df['EMA60'].shift(1)) & (df['ADX'] >= 20) & (df['DI+'] < df['DI-'])
            latest = df.iloc[-1]
            date_str = latest.name.strftime('%Y-%m-%d')
            price_str = f"${latest['Close']:.2f}"
            messages = []
            if latest['Buy_Signal']:
                messages.append(f"📈 [{symbol}] 매수 시그널 발생!\n날짜: {date_str}\n가격: {price_str}")
            if latest['Sell_Signal']:
                messages.append(f"📉 [{symbol}] 매도 시그널 발생!\n날짜: {date_str}\n가격: {price_str}")
            if not messages:
                messages.append(f"📊 [{symbol}] {date_str} 시그널 없음. 현재 가격: {price_str}")
            for msg in messages:
                bot.send_message(chat_id=CHAT_ID, text=msg)
        except Exception as e:
            bot.send_message(chat_id=CHAT_ID, text=f"[{symbol}] 에러 발생: {e}")

if __name__ == "__main__":
    send_signals()
