import ccxt
import datetime
import pandas as pd
import pandas_ta as ta
import time 
import json

#visualisation

import matplotlib.pyplot as plt
import seaborn as sns

### PARAMETERS

exchange='bybit'
symbol = 'BTC/USDT'
timeframe = '15m'  # 1 day : 1D timeframe
size=0.0005



# Open the JSON file to read the key and secret


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
    },
    'apiKey': key_value,
    'secret': secret_value 
})




def fetch_price(symbol):
    price=exchange.fetchOrderBook(symbol)
    return price['bids'][0][0],price['asks'][0][0]

def check_orders(symbol):
    return exchange.fetchOpenOrders(symbol)


def logic_exec(symbol,size,timeframe,price,id):
    # Get the OHLCV (Open, High, Low, Close, Volume) data
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=None, limit=300)

    # creating dataframe of ohlcv
    df=pd.DataFrame(ohlcv)

    ### PSAR
    d=ta.psar(df[2],df[3],df[4],0.06,0.06,0.6)

    

    # taking latest value only
    latest_val=d.iloc[-1]

    ### creating logic


    if latest_val['PSARl_0.06_0.6']>0:
        if id=='':
            price,_=fetch_price(symbol)
            # order = exchange.create_order (symbol, 'market', 'buy', size,price, params={})
            order = exchange.create_order(symbol, 'market', 'buy', size)

            id=order['info']['orderId']
            print('buy')
        print('long execution inlive')
        
            
    elif latest_val['PSARs_0.06_0.6']>0:
        if id!='':
            size=exchange.fetchBalance(params={'type': 'spot',})[f"{symbol.split('/')[0]}"]['free']
            order = exchange.create_order (symbol, 'market', 'sell', size)
            id=''
            print('sell')
        print('short execution inlive')

    plt.figure(figsize=(20,10))
    sns.lineplot(x=df[0],y=df[4],data=df)
    sns.scatterplot(x=df[0],y=d['PSARs_0.06_0.6'],data=df,color='red')
    sns.scatterplot(x=df[0],y=d['PSARl_0.06_0.6'],data=df,color='green')

    plt.savefig(f'./images/plot.png')

    time.sleep(60)



    return logic_exec(symbol,size,timeframe,price,id)


if __name__ == '__main__':

    logic_exec(symbol,size,timeframe,fetch_price(symbol)[0],id='1')


# Print the fetched data
