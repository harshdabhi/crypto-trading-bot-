
import pandas as pd
import datetime
import ccxt
from datetime import datetime, timezone, timedelta

import pandas as pd
import pandas_ta as ta
import time 
import json
import numpy as np

#visualisation
import matplotlib.pyplot as plt
import seaborn as sns


exchange='bybit'
symbol = 'BTC/USDT:USDT'
timeframe = '3m'  # 1 day : 1D timeframe
size=0.001
limit=5000
stoploss=20
takeprofit=20
deviation=1
unrealisedPnl=0.001

with open('./file.json') as f:
    data = json.load(f)

# Access the values from the loaded JSON data
key_value = data["key"]
secret_value = data["secret"]


# Initialize the exchange
exchange = eval(f'ccxt.{exchange}')({
    'enableRateLimit': True, 
    'options': {
        'adjustForTimeDifference': True,
        'recvWindow': 500000,
        'defaultType': 'swap',    
        'timeDifference': 5000
    },
    'apiKey': key_value,
    'secret': secret_value 
})



def fetch_price(symbol):
    price=exchange.fetchTicker(symbol.split(':')[0])['last']
    return price
    

def check_open_orders(symbol):
    return exchange.fetchOpenOrders(symbol)


def get_latest_position(symbol):
    positions = exchange.fetch_positions(symbol)
    contracts = positions[0]['contracts']
    pnl=positions[0]['info']['unrealisedPnl']
    return contracts,pnl


def open_long(symbol,amount):
    side='buy'
    type='limit'
    amount=size
    price=fetch_price(symbol)
    params={
        'TakeProfit': {
            'type': 'limit',  # or 'market', this field is not necessary if limit price is specified
            'price': price+stoploss,  # limit price for a limit stop loss order
            'triggerPrice': price+stoploss,
        },
        
    }
    order = exchange.create_order(symbol, type, side, amount, price,params)
    return order


def open_short(symbol,amount):
    side='sell'
    type='limit'
    amount=size
    price=fetch_price(symbol)
    params={
        'TakeProfit': {
            'type': 'limit',  # or 'market', this field is not necessary if limit price is specified
            'price': price-takeprofit,  # limit price for a limit stop loss order
            'triggerPrice': price-takeprofit+deviation,
        },
        
    }
    order = exchange.create_order(symbol, type, side, amount, price,params)
    return order




def logic_exec(symbol,size,timeframe,price,id,isLong,isShort):
    # Get the OHLCV (Open, High, Low, Close, Volume) data
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=None, limit=300)

    # creating dataframe of ohlcv
    df=pd.DataFrame(ohlcv)

    ### PSAR
    d=ta.psar(df[2],df[3],df[4],0.06,0.06,0.6)
    d1=ta.ema(df[4][-14:-1],13).iloc[-1]

    

    # taking latest value only
    latest_val=d.iloc[-1]

    ### creating logic
    _,latest_position_detail=get_latest_position(symbol)

    print('program is running')

    
    if latest_val['PSARl_0.06_0.6']>0 and latest_val['PSARr_0.06_0.6']==1:
        if id==None and df[4].iloc[-1]>d1:
            order=open_long(symbol,size)
            id=order['id']
            isLong=True
            print('buy')

        elif id!=None and isShort:
            side = 'sell'
            type='limit'
            price=fetch_price(symbol)
            params = {
                'reduce_only': True
            }
            amount=size
            exchange.createOrder(symbol, type, side, amount, price, params)
            isLong=False
            id=None
            print('Long position close has been placed')

        



            #####  if condition for stop loss triggers 

            
    elif latest_val['PSARs_0.06_0.6']>0 and latest_val['PSARr_0.06_0.6']==1:
        if id==None and df[4].iloc[-1]<d1:
            order=open_short(symbol,size)
            id=order['id']
            isShort=True
            print('sell')

        elif id!=None and isLong:
            side = 'buy'
            type='limit'
            amount=size
            price=fetch_price(symbol)
            params = {
                'reduce_only': True
            }
            exchange.createOrder(symbol, type, side, amount, price, params)
            isShort=False
            id=None
            print('Short position close has been placed')
        




    time.sleep(5)


    
    return logic_exec(symbol,size,timeframe,price,id,isLong,isShort)

if __name__ == '__main__':

    logic_exec(symbol,size,timeframe,fetch_price(symbol),id=None,isLong=False,isShort=False)

