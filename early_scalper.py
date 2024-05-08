
import pandas as pd
import datetime
import ccxt
from datetime import datetime, timezone, timedelta

import pandas as pd
import pandas_ta as ta
import time 
import json
import numpy as np

from flask import Flask, render_template
from flask_cors import CORS

#visualisation
import matplotlib.pyplot as plt
import seaborn as sns

import threading


with open('./file_bitmex.json') as f:
    data = json.load(f)

    # Access the values from the loaded JSON data
    key_value = data["key"]
    secret_value = data["secret"]
    password_file = data["password"]

class bitmex_trading_bot:

    def __init__(self,exchange:str="bitmex",symbol:str="XBTUSDT",timeframe:str="1h",size:int=1000,limit:int=1000,takeprofit:float=25,stoploss:float=20):

        """
        Initialize the trading bot with default values for the exchange, symbol, timeframe, size, limit, take profit, and stop loss.
        
        Parameters:
            exchange (str): Name of the exchange. Default is "bitmex".
            symbol (str): Symbol for trading. Default is "XBTUSDT".
            timeframe (str): Timeframe for trading. Default is "5m".
            size (int): Size of the trade. Default is 2000.
            limit (int): Limit for the trade. Default is 100.
            takeprofit (int): Take profit percentage. Default is 25.`
            stoploss (int): Stop loss percentage. Default is 20.
        
        Returns:
            None
        """
        
        self.exchange=exchange
        self.symbol = symbol
        self.timeframe = timeframe
        self.size=size
        self.limit=limit
        self.takeprofit=takeprofit
        self.stoploss=stoploss
        self.id=None
        self.isLong=False
        self.isShort=False


        # Initialize the exchange
        self.exchange_conn = eval(f'ccxt.{self.exchange}')({
            'enableRateLimit': True, 
            'options': {
                'adjustForTimeDifference': True,
                'recvWindow': 50000,
                'defaultType': 'swap',    
                'timeDifference': 5000
            },
            'apiKey': key_value,
            'secret': secret_value 
            })



    # fetching the latest price
    def fetch_price(self):
        ''' 
        return: float=price

        '''
        price=self.exchange_conn.fetchTicker(self.symbol)['info']['lastPrice']
        return float(price)
        

    def check_open_orders(self):
        '''
        return: list = open orders
        '''
        return self.exchange_conn.fetchOpenOrders(self.symbol)



    def open_long(self):
       
        price=self.fetch_price(self.symbol)
        self.exchange.privatePostOrder({"symbol":f"{self.symbol}",
                                "ordType":"Limit",
                                "side":"Buy",
                                "timeInForce":"GTC",
                                "quantity":f"{self.size}",
                                "price":f"{price}",
                                "execInst":"ParticipateDoNotInitiate"})
        return price
        
        


    def open_short(self):
        price=self.fetch_price()
        self.exchange_conn.privatePostOrder({"symbol":f"{self.symbol}",
                                "ordType":"Limit",
                                "side":"Sell",
                                "timeInForce":"GTC",
                                "quantity":f"{self.size}",
                                "price":f"{price}",
                                "execInst":"ParticipateDoNotInitiate"})
        return price
        

    def close_short(self):
        price=self.fetch_price()
        self.exchange_conn.privatePostOrder({"symbol":f"{self.symbol}",
                        "ordType":"Limit",
                        "side":"Buy",
                        "timeInForce":"GTC",
                        "quantity":f"{self.size}",
                        "price":f"{price}",
                        "execInst":"ReduceOnly,ParticipateDoNotInitiate"})
        


    def close_long(self):
        price=self.fetch_price()
        self.exchange_conn.privatePostOrder({"symbol":f"{self.symbol}",
                        "ordType":"Limit",
                        "side":"Sell",
                        "timeInForce":"GTC",
                        "quantity":f"{self.size}",
                        "price":f"{price}",
                        "execInst":"ReduceOnly,ParticipateDoNotInitiate"})
        
        
    def take_profit_long(self):
        price=float(self.exchange_conn.private_get_position({"symbol":self.symbol})[0]['avgEntryPrice'])
        while self.exchange_conn.fetchOpenOrders(self.symbol)==[]:
            self.exchange_conn.privatePostOrder({"symbol":f"{self.symbol}",
                                        "ordType":"Limit",
                                        "side":"Sell",
                                        "timeInForce":"GTC",
                                        "quantity":f"{self.size}",
                                        "price":f"{price+self.takeprofit}",
                                        "execInst":"ReduceOnly"})
            self.takeprofit+=1
            time.sleep(2)

        

    def take_profit_short(self):
        price=float(self.exchange_conn.private_get_position({"symbol":self.symbol})[0]['avgEntryPrice'])
        while self.exchange_conn.fetchOpenOrders(self.symbol)==[]:
            self.exchange_conn.privatePostOrder({"symbol":f"{self.symbol}",
                                        "ordType":"Limit",
                                        "side":"Buy",
                                        "timeInForce":"GTC",
                                        "quantity":f"{self.size}",
                                        "price":f"{price-self.takeprofit}",
                                        "execInst":"ReduceOnly"})
            
            self.takeprofit+=1
            time.sleep(2)

                    


    def check_position(self):
        try:
            x=self.exchange_conn.private_get_position({"symbol":self.symbol})
            if x==[]:
                return False
            
            else:
                return x[0]['isOpen']
            
        except:
            return False


    def logic_exec(self,isLong=False,isShort=False):


        ohlcv = self.exchange_conn.fetch_ohlcv(self.symbol, self.timeframe, since=None, limit=self.limit)
        data=pd.DataFrame(ohlcv,columns=['datetime','Open','High','Low','Close','Volume'])
        data



        len = 15
        FfastLength = 8
        FslowLength = 21
        FsignalLength = 9
        tuning_ema=55

        ema1 = ta.ema(data.Close, len)
        ema2 = ta.ema(ema1, len)
        ema3 = ta.ema(ema2, len)


        ema_filter=ta.ema(data.Close,tuning_ema)
        avg = 3 * (ema1 - ema2) + ema3


        Fsource = data.Close
        FfastMA = ta.ema(Fsource, FfastLength)
        FslowMA = ta.ema(Fsource, FslowLength)
        Fmacd = FfastMA - FslowMA
        Fsignal = ta.sma(Fmacd, FsignalLength)

        data['Fmacd'] = Fmacd
        data['Fsignal'] = Fsignal
        data['avg'] = avg
        data['ema_filter']=ema_filter

        # Shift the columns to get the previous values
        data['Fmacd_prev'] = data['Fmacd'].shift(1)
        data['Fsignal_prev'] = data['Fsignal'].shift(1)
        data['avg_prev'] = data['avg'].shift(1)

        # Apply the function row-wise
        data['long_signal'] = (ta.cross_value(data['Fmacd'], data['Fsignal']) & (data['avg'] > data['avg_prev'])).astype(int)
        data['short_signal'] = (ta.cross_value(data['Fsignal'], data['Fmacd']) & (data['avg_prev']>data['avg'])).astype(int)

        islong=False
        isShort=False

         #visualisation###
        plt.figure(figsize=(60, 60))
        sns.lineplot(data=data, x=data.index, y='Close', color='blue')  # Plot the lineplot without markers
        sns.lineplot(data=data, x=data.index, y='ema_filter', color='blue')  # Plot the lineplot without markers

        # Plot markers at True values of long_signal and short_signal
        true_values_long = data[data.long_signal == 1].index
        true_values_short = data[data.short_signal == 1].index

        # Find the intersection of indices where both long_signal and short_signal are 1
        true_values_both = data[(data.long_signal == 1) & (data.short_signal == 1)].index

        plt.scatter(true_values_long, data[data.long_signal==1].Close, color='green', marker='*', label='Long Signal', s=500)
        plt.scatter(true_values_short, data[data.short_signal==1].Close, color='red', marker='*', label='Short Signal', s=500)

        plt.savefig('img.png')




        if data['long_signal'].iloc[-1] and data.Close.iloc[-1]>ema_filter.iloc[-1]:
            try:
                self.islong=True
                retries_no=10
                while self.check_position() != True and retries_no>0:
                    self.exchange_conn.private_delete_order_all({"symbol": self.symbol})
                    time.sleep(5)
                    self.open_long()
                    time.sleep(30)
                    retries_no-=1
                    print("long")
                    if retries_no==1:
                        raise Exception

            except:
                self.islong=False

        elif data['short_signal'].iloc[-1] and data.Close.iloc[-1]<ema_filter.iloc[-1]:
            try:
                retries_order = 10
                self.isShort=True
                while self.check_position() != True and retries_order > 0:
                    self.exchange_conn.private_delete_order_all({"symbol": self.symbol})
                    time.sleep(5)
                    self.open_short()
                    print('sell')
                    time.sleep(30)
                    retries_order -= 1
                    if retries_order == 1:
                        raise Exception
            except:
                self.isShort=False

        elif data['long_signal'].iloc[-1] and islong:
            while self.check_position() != False:
                self.exchange_conn.private_delete_order_all({"symbol": self.symbol})
                self.close_long()
                time.sleep(20)
                print("close long")

        elif data['short_signal'].iloc[-1] and isShort:
            while self.check_position() != False:
                self.close_short()
                time.sleep(20)
                self.exchange_conn.private_delete_order_all({"symbol": self.symbol})
                print("close short")

        print('App is running')
        time.sleep(300)

        return self.isLong,self.isShort
    


class StreamlitApp:
    def __init__(self):
        self.is_running = False
        self.bot=None
        

    def run(self):
        bot=bitmex_trading_bot()
        x,y=bot.logic_exec()

        while True:
            x,y=bot.logic_exec(x,y)
          

app = Flask(__name__)
CORS(app)


@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':

    retries=5
    while retries>0:
        running=False
        try:
            thread = threading.Thread(target=app.run, kwargs={
                                    'debug': False, 'host': '0.0.0.0', 'port': 8080})
            thread.start()


            if running!=True:
            
                bot = StreamlitApp()
                bot.run()
                running=True

        except Exception as e:
            print(f"An error occurred: {e}")
            retries -= 1
            print(f"Retrying in 10 seconds... (Retry {retries}/5)")
            time.sleep(10)

    





