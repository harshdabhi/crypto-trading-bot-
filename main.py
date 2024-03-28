
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
    password_file = data["password"]

class bitmex_trading_bot:


    def __init__(self,exchange:str="bitmex",symbol:str="XBTUSDT",timeframe:str="5m",size:int=2000,limit:int=100,takeprofit:float=25,stoploss:float=20):

        """
        Initialize the trading bot with default values for the exchange, symbol, timeframe, size, limit, take profit, and stop loss.
        
        Parameters:
            exchange (str): Name of the exchange. Default is "bitmex".
            symbol (str): Symbol for trading. Default is "XBTUSDT".
            timeframe (str): Timeframe for trading. Default is "5m".
            size (int): Size of the trade. Default is 2000.
            limit (int): Limit for the trade. Default is 100.
            takeprofit (int): Take profit percentage. Default is 25.
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
                        "execInst":"ReduceOnly"})
        


    def close_long(self):
        price=self.fetch_price()
        self.exchange_conn.privatePostOrder({"symbol":f"{self.symbol}",
                        "ordType":"Limit",
                        "side":"Sell",
                        "timeInForce":"GTC",
                        "quantity":f"{self.size}",
                        "price":f"{price}",
                        "execInst":"ReduceOnly"})
        
        
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


    def logic_exec(self,id=None,isLong=False,isShort=False):


        # Get the OHLCV (Open, High, Low, Close, Volume) data
        ohlcv = self.exchange_conn.fetch_ohlcv(self.symbol, self.timeframe, since=None, limit=self.limit)

        # creating dataframe of ohlcv
        df=pd.DataFrame(ohlcv)


        df['ema'] = ta.ema(df[4], window=13)

        ### PSAR
        d=ta.psar(df[2],df[3],df[4],0.06,0.06,0.6)
        d1=ta.ema(df[4][-14:-1],13).iloc[-1]

        ### plotting chart for visualisation ######
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
            if self.id==None and df[4].iloc[-1]>d1 and self.isLong!=True:
                try:
                    retries_order=5
                    while self.check_position()!=True and retries_order>0:
                        self.exchange_conn.private_delete_order_all({"symbol":self.symbol})
                        time.sleep(1)
                        self.open_long()
                        time.sleep(3)
                        print('buy')
                        retries_order-=1
                        if retries_order==1:
                            raise Exception


                    self.take_profit_long()
                    
                    

                    self.id=True
                    self.isLong=True

                except:
                    self.id=None
                    self.isLong=False
                    print('Order Failed for long position')


            elif self.id!=None and self.isShort:
                print('Short position close has been placed')

                while(self.check_position()):
                    self.exchange_conn.private_delete_order_all({"symbol":self.symbol})
                    self.close_short()
                    time.sleep(3)

                self.isLong=False
                self.id=None

            


                
        elif latest_val['PSARs_0.06_0.6']>0 and latest_val['PSARr_0.06_0.6']==1:
            if self.id==None and df[4].iloc[-1]<d1 and self.isShort!=True:

                try:
                    retries_order=5
                
                    while self.check_position()!=True and retries_order>0:
                        self.exchange_conn.private_delete_order_all({"symbol":self.symbol})
                        time.sleep(1)
                        self.open_short()
                        print('sell')
                        time.sleep(3)
                        retries_order-=1
                        if retries_order==1:
                            raise Exception

                    self.take_profit_short()
                    

                    self.id=True
                    self.isShort=True

                except:
                    self.id=None
                    self.isShort=False
                    print('Order Failed for short position')


            elif self.id!=None and self.isLong:
                print('Long position close has been placed')

                while(self.check_position()):
                    self.close_long()
                    time.sleep(3)

                                
                self.isShort=False
                self.id=None
            



        time.sleep(15)

        x=self.check_position()
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
        # if self.is_running:
        #     st.title("Bitmex Trading Bot")
        #     exchange = st.text_input("Exchange", value="bitmex", help="Name of the exchange", key="exchange_input")
        #     symbol = st.text_input("Symbol", value="XBTUSDT", help="Trading symbol", key="symbol_input")
        #     timeframe = st.text_input("Timeframe", value="5m", help="Timeframe for trading", key="timeframe_input")
        #     size = st.number_input("Size", value=1000, help="Trade size", key="size_input")
        #     limit = st.number_input("Limit", value=1000, help="Limit for orders", key="limit_input")
        #     take_profit = st.number_input("Take Profit", value=20, help="Take profit percentage", key="take_profit_input")
        #     stop_loss = st.number_input("Stop Loss", value=20, help="Stop loss percentage", key="stop_loss_input")

        #     if st.button("Stop Bot", key="stop_bot_button"):
        #         self.is_running = False
        #         st.warning("Bot stopped.")
        # else:
        
        #     if st.button("Start Bot", key="start_bot_button"):
        #         bot_start = bitmex_trading_bot(exchange,symbol,timeframe,size,limit,take_profit,stop_loss)
        #         bot_start.is_running = True
        #         bot_start.logic_exec(None, False, False, None)
        #         st.success("Bot started successfully.")


        bot=bitmex_trading_bot()
        bot.logic_exec()
          



if __name__ == "__main__":

    max_retries = 5  # Maximum number of retries
    retries = 0

    while retries < max_retries:
        try:
            app = StreamlitApp()
            app.run()
            
        except Exception as e:
            print(f"An error occurred: {e}")
            retries += 1
            print(f"Retrying in 10 seconds... (Retry {retries}/{max_retries})")
            time.sleep(10)  # Wait for 10 seconds before retrying

    





