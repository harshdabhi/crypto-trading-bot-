
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
timeframe = '1m'  # 1 day : 1D timeframe
size=0.001
limit=5000
stoploss=50
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
        'recvWindow': 5000,
        'defaultType': 'swap',    
    },
    'apiKey': key_value,
    'secret': secret_value 
})



def fetch_price(symbol):
    # price=exchange.fetchTicker(symbol.split(':')[0])['last']
    price=exchange.fetchOrderBook(symbol)['bids'][0][0]
    return price
    

def check_open_orders(symbol):
    return exchange.fetchOpenOrders(symbol)


def get_latest_position(symbol):
    positions = exchange.fetch_positions(symbol)
    contracts = positions[0]['contracts']
    pnl=positions[0]['info']['unrealisedPnl']
    id=positions[0]['id']
    return id,contracts,pnl


def open_long(symbol,amount):
    side='buy'
    type='limit'
    amount=size
    price=fetch_price(symbol)
    params={
        'stopLoss': {
            'type': 'limit',  # or 'market', this field is not necessary if limit price is specified
            'price': price-stoploss,  # limit price for a limit stop loss order
            'triggerPrice': price-stoploss+deviation,
        },
        'takeProfit': {
            'type': 'limit',  # or 'market', this field is not necessary if limit price is specified
            'price': price+stoploss,  # limit price for a limit take profit order
            'triggerPrice': price+stoploss-deviation,
        },
        
    }
    order = exchange.create_order(symbol, type, side, amount, price,params)
    take_profit=price+stoploss
    return order,take_profit


def open_short(symbol,amount):
    side='sell'
    type='limit'
    amount=size
    price=fetch_price(symbol)
    params={
        'stopLoss': {
            'type': 'limit',  # or 'market', this field is not necessary if limit price is specified
            'price': price+stoploss,  # limit price for a limit stop loss order
            'triggerPrice': price+stoploss-deviation,
        },
        'takeProfit': {
            'type': 'limit',  # or 'market', this field is not necessary if limit price is specified
            'price': price-stoploss,  # limit price for a limit take profit order
            'triggerPrice': price-stoploss+deviation,
        },
        
    }
    order = exchange.create_order(symbol, type, side, amount, price,params)
    take_profit=price-stoploss
    return order,take_profit




def logic_exec(symbol,size,timeframe,price,id,isLong,isShort,trail_price,takeprofit_price):
    # Get the OHLCV (Open, High, Low, Close, Volume) data
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=None, limit=300)

    # creating dataframe of ohlcv
    df=pd.DataFrame(ohlcv)

    ### PSAR
    d=ta.psar(df[2],df[3],df[4],0.06,0.06,0.6)

    

    # taking latest value only
    latest_val=d.iloc[-1]

    ### creating logic
    position,_,latest_position_detail=get_latest_position(symbol)


    try:
        if latest_val['PSARl_0.06_0.6']>0:
            if id==None :
                order,takeprofit_price=open_long(symbol,size)
                id=order['id']
                isLong=True
                print('buy')

            

            elif id!=None and isShort:
                side = 'sell'
                type='market'
                price=fetch_price(symbol)
                params = {
                    'reduce_only': True
                }
                amount=size
                close_position_order = exchange.createOrder(symbol, type, side, amount, price, params)
                isLong=False
                id=None
                print('Long position close has been placed')

                #####  if condition for stop loss triggers 

                
        elif latest_val['PSARs_0.06_0.6']>0:
            if id==None:
                order,takeprofit_price=open_short(symbol,size)
                id=order['id']
                isShort=True
                print('sell')

        

            elif id!=None and isLong:
                side = 'buy'
                type='market'
                amount=size
                price=fetch_price(symbol)
                params = {
                    'reduce_only': True
                }
                close_position_order = exchange.createOrder(symbol, type, side, amount, price, params)
                isShort=False
                id=None
                print('Short position close has been placed')
    except:
        pass



    try:
        if float(latest_position_detail)>=unrealisedPnl:
            price=fetch_price(symbol)
            
            if isLong and trail_price<price:
                exchange.cancel_all_orders(symbol)
                exchange.createStopLossOrder(symbol, type='market', side='sell', amount=size, price=price, stopLossPrice=price-stoploss+deviation)
                exchange.createTakeProfitOrder(symbol, type='limit', side='sell', amount=size, price=takeprofit_price, takeProfitPrice=takeprofit_price-deviation)
                trail_price=price
                print('stop loss updated for long')
                
            elif isShort and trail_price>price:
                exchange.cancel_all_orders(symbol)
                exchange.createStopLossOrder(symbol, type='market', side='buy', amount=size, price=price, stopLossPrice=price+stoploss-deviation)
                exchange.createTakeProfitOrder(symbol, type='limit', side='buy', amount=size, price=takeprofit_price, takeProfitPrice=takeprofit_price+deviation)

                trail_price=price
                print('stop loss updated for short')
        
    except:
        pass
    
    time.sleep(4)


    try:
        x=exchange.fetch_positions(symbol)[0]['side']
        if x==None:
            exchange.cancel_all_orders(symbol)
            print('no position')
            id=None
            isLong=False
            isShort=False

    except:
        pass



    
    return logic_exec(symbol,size,timeframe,price,id,isLong,isShort,trail_price,takeprofit_price)


logic_exec(symbol,size,timeframe,fetch_price(symbol),id=None,isLong=False,isShort=False,trail_price=0,takeprofit_price=0)
