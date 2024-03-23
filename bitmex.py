
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

#streamlit
import streamlit as st

with open('./file_bitmex.json') as f:
    data = json.load(f)

    # Access the values from the loaded JSON data
    key_value = data["key"]
    secret_value = data["secret"]

class bitmex_trading_bot:


    def __init__(self,exchange:str="bitmex",symbol:str="XBTUSDT",timeframe:str="5m",size:int=1000,limit:int=1000,takeprofit:int=20,stoploss:int=20):
        
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
        price=self.fetch_price(self.symbol)
        self.exchange_conn.privatePostOrder({"symbol":f"{self.symbol}",
                                "ordType":"Limit",
                                "side":"Sell",
                                "timeInForce":"GTC",
                                "quantity":f"{self.size}",
                                "price":f"{price}",
                                "execInst":"ParticipateDoNotInitiate"})
        return price
        

    def close_short(self):
        price=self.fetch_price(self.symbol)
        self.exchange_conn.privatePostOrder({"symbol":f"{self.symbol}",
                        "ordType":"Limit",
                        "side":"Buy",
                        "timeInForce":"GTC",
                        "quantity":f"{self.size}",
                        "price":f"{price}",
                        "execInst":"ReduceOnly"})
        


    def close_long(self):
        price=self.fetch_price(self.symbol)
        self.exchange_conn.privatePostOrder({"symbol":f"{self.symbol}",
                        "ordType":"Limit",
                        "side":"Sell",
                        "timeInForce":"GTC",
                        "quantity":f"{self.size}",
                        "price":f"{price}",
                        "execInst":"ReduceOnly"})
        
        



    def logic_exec(self,id=None,isLong=False,isShort=False):


        # Get the OHLCV (Open, High, Low, Close, Volume) data
        ohlcv = self.exchange_conn.fetch_ohlcv(self.symbol, self.timeframe, since=None, limit=self.limit)

        # creating dataframe of ohlcv
        df=pd.DataFrame(ohlcv)


        df['ema'] = ta.ema(df[4], window=13)

        ### PSAR
        d=ta.psar(df[2],df[3],df[4],0.06,0.06,0.6)
        d1=ta.ema(df[4][-14:-1],13).iloc[-1]

        #### plotting chart for visualisation ######
        plt.figure(figsize=(40,20))
        sns.lineplot(x=df[0],y=df[4],data=df)
        sns.scatterplot(x=df[0],y=d['PSARs_0.06_0.6'],data=df,color='red')
        sns.scatterplot(x=df[0],y=d['PSARl_0.06_0.6'],data=df,color='green')
        sns.lineplot(x=df[0],y=df['ema'],color='brown')
        plt.savefig(f'./images/plot.png')
        plt.close()
        

    ##### getting latest value of candle and PSAR ####
        latest_val=d.iloc[-1]



    ### creating logic  #####
        
        if latest_val['PSARl_0.06_0.6']>0 and latest_val['PSARr_0.06_0.6']==1:
            if self.id==None and df[4].iloc[-1]>d1:

                while self.exchange_conn.private_get_position({"symbol":self.symbol})[0]['isOpen']!=True:
                    self.exchange_conn.private_delete_order_all({"symbol":self.symbol})
                    price=self.open_long(self.symbol,self.size)
                    time.sleep(5)
                    print('buy')


                self.exchange_conn.privatePostOrder({"symbol":f"{self.symbol}",
                                "ordType":"Limit",
                                "side":"Sell",
                                "timeInForce":"GTC",
                                "quantity":f"{self.size}",
                                "price":f"{price+self.takeprofit}",
                                "execInst":"ReduceOnly"})
                

                self.id=True
                self.isLong=True


            elif self.id!=None and self.isShort:
                print('Short position close has been placed')

                while(self.exchange_conn.private_get_position({"symbol":self.symbol})[0]['isOpen']):
                    self.exchange_conn.private_delete_order_all({"symbol":self.symbol})
                    self.close_short(self.symbol,self.size)
                    time.sleep(5)

                self.isLong=False
                self.id=None

            


                
        elif latest_val['PSARs_0.06_0.6']>0 and latest_val['PSARr_0.06_0.6']==1:
            if self.id==None and df[4].iloc[-1]<d1:
                
                while self.exchange_conn.private_get_position({"symbol":self.symbol})[0]['isOpen']!=True:
                    self.exchange_conn.private_delete_order_all({"symbol":self.symbol})
                    price=self.open_short(self.symbol,self.size)
                    print('sell')
                    time.sleep(5)

                
                self.exchange_conn.privatePostOrder({"symbol":f"{self.symbol}",
                                "ordType":"Limit",
                                "side":"Buy",
                                "timeInForce":"GTC",
                                "quantity":f"{self.size}",
                                "price":f"{price-self.takeprofit}",
                                "execInst":"ReduceOnly"})
                

                self.id=True
                self.isShort=True


            elif self.id!=None and self.isLong:
                print('Long position close has been placed')

                while(self.exchange_conn.private_get_position({"symbol":self.symbol})[0]['isOpen']):
                    self.close_long(self.symbol,self.size)
                    time.sleep(5)

                                
                self.isShort=False
                self.id=None
            



        time.sleep(15)

        x=self.exchange_conn.private_get_position({"symbol":self.symbol})[0]['isOpen']
        if x==False:
            self.exchange_conn.private_delete_order_all({"symbol":self.symbol})
            self.id=None
            self.isLong=False
            self.isShort=False

        elif x==True:
            time.sleep(300)

        return self.logic_exec(self.id,self.isLong,self.isShort)
    


class StreamlitApp:
    def __init__(self):
        self.is_running = False
        self.bot=None
        

    def run(self):
        st.title("Bitmex Trading Bot")

        exchange = st.text_input("Exchange", value="bitmex", help="Name of the exchange")
        symbol = st.text_input("Symbol", value="XBTUSDT", help="Trading symbol")
        timeframe = st.text_input("Timeframe", value="5m", help="Timeframe for trading")
        size = st.number_input("Size", value=1000, help="Trade size")
        limit = st.number_input("Limit", value=1000, help="Limit for orders")
        take_profit = st.number_input("Take Profit", value=20, help="Take profit percentage")
        stop_loss = st.number_input("Stop Loss", value=20, help="Stop loss percentage")

        if self.is_running!=True:
            if st.button("Start Bot"):
                bot_start = bitmex_trading_bot(exchange, symbol, timeframe, size, limit, take_profit, stop_loss)
                bot_start.logic_exec(None, False, False)
                self.is_running = True
                st.success("Bot started successfully.")
            



if __name__ == "__main__":
    app = StreamlitApp()
    app.run()





