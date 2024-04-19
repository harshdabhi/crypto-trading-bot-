
import pandas as pd
import datetime
import ccxt
from datetime import datetime, timezone, timedelta

import pandas as pd
import pandas_ta as ta
import time
import json
import numpy as np

# visualisation
import matplotlib.pyplot as plt
import seaborn as sns
import threading

from flask import Flask, render_template
from flask_cors import CORS


with open('./file_bitmex.json') as f:
    data = json.load(f)

    # Access the values from the loaded JSON data
    key_value = data["key"]
    secret_value = data["secret"]
    password_file = data["password"]


class bitmex_trading_bot:

    def __init__(self, exchange: str = "bitmex", symbol: str = "XBTUSDT", timeframe: str = "5m", size: int = 250000, limit: int = 100, takeprofit: float = 5, stoploss: float = 20):
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

        self.exchange = exchange
        self.symbol = symbol
        self.timeframe = timeframe
        self.size = size
        self.limit = limit
        self.takeprofit = takeprofit
        self.stoploss = stoploss
        self.id = None
        self.isLong = False
        self.isShort = False

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

    def fetch_price(self, type):
        ''' 
        return: float=price

        '''
        # price = self.exchange_conn.fetchTicker(
        #     self.symbol)['info']['lastPrice']

        if type == 'long':
            price = self.exchange_conn.fetch_order_book(
                self.symbol, limit=2)['bids'][0][0]

        elif type == 'short':
            price = self.exchange_conn.fetch_order_book(
                self.symbol, limit=2)['asks'][0][0]

        return float(price)

    def check_open_orders(self):
        '''
        return: list = open orders
        '''
        return self.exchange_conn.fetchOpenOrders(self.symbol)

    def open_long(self):

        price = self.fetch_price('long')
        deviation = 0.1
        self.exchange_conn.privatePostOrder({"symbol": f"{self.symbol}",
                                             "ordType": "Limit",
                                             "side": "Buy",
                                             "timeInForce": "GTC",
                                             "quantity": f"{self.size}",
                                             "price": f"{price-deviation}",
                                             "execInst": "ParticipateDoNotInitiate"})
        return price

    def open_short(self):
        price = self.fetch_price('short')
        deviation = 0.1
        self.exchange_conn.privatePostOrder({"symbol": f"{self.symbol}",
                                             "ordType": "Limit",
                                             "side": "Sell",
                                             "timeInForce": "GTC",
                                             "quantity": f"{self.size}",
                                             "price": f"{price+deviation}",
                                             "execInst": "ParticipateDoNotInitiate"})
        return price

    def close_short(self):
        price = self.fetch_price('long')
        size = self.exchange_conn.private_get_position(
            {"symbol": self.symbol})[0]['currentQty']
        size = float(size)*-1

        self.exchange_conn.privatePostOrder({"symbol": f"{self.symbol}",
                                             "ordType": "Limit",
                                             "side": "Buy",
                                             "timeInForce": "GTC",
                                             "quantity": f"{size}",
                                             "price": f"{price}",
                                             "execInst": "ReduceOnly,ParticipateDoNotInitiate"})

    def close_long(self):
        price = self.fetch_price('short')

        size = self.exchange_conn.private_get_position(
            {"symbol": self.symbol})[0]['currentQty']
        size = float(size)

        self.exchange_conn.privatePostOrder({"symbol": f"{self.symbol}",
                                             "ordType": "Limit",
                                             "side": "Sell",
                                             "timeInForce": "GTC",
                                             "quantity": f"{size}",
                                             "price": f"{price}",
                                             "execInst": "ReduceOnly,ParticipateDoNotInitiate"})

    def take_profit_long(self):

        if self.check_position() == True:

            #self.exchange_conn.private_delete_order_all({"symbol": f"{self.symbol}"})

            price = float(self.exchange_conn.private_get_position(
                {"symbol": self.symbol})[0]['avgEntryPrice'])

            size = self.exchange_conn.private_get_position(
                {"symbol": self.symbol})[0]['currentQty']
            size = float(size)

            temp = self.takeprofit

            #while self.exchange_conn.fetchOpenOrders(self.symbol) == []:

            self.exchange_conn.privatePostOrder({"symbol": f"{self.symbol}",
                                                "ordType": "Limit",
                                                    "side": "Sell",
                                                    "timeInForce": "GTC",
                                                    "quantity": f"{size}",
                                                    "price": f"{price+temp}",
                                                    "execInst": "ReduceOnly"})

                #temp += 2
            time.sleep(2)

    def take_profit_short(self):

        if self.check_position() == True:
            self.exchange_conn.private_delete_order_all(
                {"symbol": f"{self.symbol}"})

            price = float(self.exchange_conn.private_get_position(
                {"symbol": self.symbol})[0]['avgEntryPrice'])

            size = self.exchange_conn.private_get_position(
                {"symbol": self.symbol})[0]['currentQty']
            size = float(size)*-1

            temp = self.takeprofit

            #while self.exchange_conn.fetchOpenOrders(self.symbol) == []:

            self.exchange_conn.privatePostOrder({"symbol": f"{self.symbol}",
                                                "ordType": "Limit",
                                                    "side": "Buy",
                                                    "timeInForce": "GTC",
                                                    "quantity": f"{self.size}",
                                                    "price": f"{price-temp}",
                                                    "execInst": "ReduceOnly"})

                # temp += 2

            time.sleep(2)

    def stop_loss_short(self):
        if self.check_position() == True:
            self.exchange_conn.private_delete_order_all(
                {"symbol": f"{self.symbol}"})

            price = float(self.exchange_conn.private_get_position(
                {"symbol": self.symbol})[0]['avgEntryPrice'])

            size = self.exchange_conn.private_get_position(
                {"symbol": self.symbol})[0]['currentQty']
            size = float(size)*-1

            temp = self.takeprofit

            while self.exchange_conn.fetchOpenOrders(self.symbol) == []:

                self.exchange_conn.privatePostOrder({"symbol": "XBTUSDT",
                                                     "ordType": "StopLimit",
                                                     "side": "Buy",
                                                     "timeInForce": "GTC",
                                                     "quantity": f"{size}",
                                                     "price": f"{price}",
                                                     "stopPx": f"{price+temp}",
                                                     "execInst": "ReduceOnly"})

                temp += 2
                time.sleep(1)

    def stop_loss_long(self):
        if self.check_position() == True:
            self.exchange_conn.private_delete_order_all(
                {"symbol": f"{self.symbol}"})

            price = float(self.exchange_conn.private_get_position(
                {"symbol": self.symbol})[0]['avgEntryPrice'])

            size = self.exchange_conn.private_get_position(
                {"symbol": self.symbol})[0]['currentQty']
            size = float(size)

            temp = self.takeprofit

            while self.exchange_conn.fetchOpenOrders(self.symbol) == []:

                self.exchange_conn.privatePostOrder({"symbol": "XBTUSDT",
                                                     "ordType": "StopLimit",
                                                     "side": "Buy",
                                                     "timeInForce": "GTC",
                                                     "quantity": f"{size}",
                                                     "price": f"{price}",
                                                     "stopPx": f"{price-temp}",
                                                     "execInst": "ReduceOnly"})

                temp += 2
                time.sleep(1)

    def check_position(self):
        try:
            x = self.exchange_conn.private_get_position(
                {"symbol": self.symbol})
            if x == []:
                return False

            else:
                return x[0]['isOpen']

        except:
            return False

    def pnl_realised_profit(self):

        pnl = float(self.exchange_conn.private_get_position(
            {"symbol": self.symbol})[0]['unrealisedPnl'])
        qty = float(self.exchange_conn.private_get_position(
            {"symbol": self.symbol})[0]['currentQty'])

        pnl = pnl/float(10**6)
        qty = qty/float(10**6)

        if qty < 0:
            qty = qty*-1
            type_to_close = 'Buy'
            expected_profit = qty*(self.takeprofit)

        else:
            type_to_close = 'Sell'
            expected_profit = qty*(self.takeprofit)

        if pnl >= expected_profit:
            return True, type_to_close

        elif pnl <= -expected_profit:
            return True, type_to_close

        else:
            return False, None

    def logic_exec(self, id=None, isLong=False, isShort=False):

        # Get the OHLCV (Open, High, Low, Close, Volume) data
        ohlcv = self.exchange_conn.fetch_ohlcv(
            self.symbol, self.timeframe, since=None, limit=self.limit)

        # creating dataframe of ohlcv
        df = pd.DataFrame(ohlcv)

        df['ema'] = ta.ema(df[4], window=13)

        # PSAR
        d = ta.psar(df[2], df[3], df[4], 0.06, 0.06, 0.6)
        d1 = ta.ema(df[4][-14:-1], 13).iloc[-1]

    ##### getting latest value of candle and PSAR ####
        latest_val = d.iloc[-1]

    ### creating logic  #####

        if latest_val['PSARl_0.06_0.6'] > 0 and latest_val['PSARr_0.06_0.6'] == 1:
            if self.id == None and df[4].iloc[-1] > d1 and self.isLong != True:
                try:
                    retries_order = 11
                    while self.check_position() != True and retries_order > 0:
                        self.exchange_conn.private_delete_order_all({"symbol": self.symbol})
                        time.sleep(1)
                        self.open_long()
                        self.open_short()
                        print('buy')
                        time.sleep(5)
                        retries_order -= 1
                        if retries_order == 1:
                            raise Exception

                    time.sleep(2)

                    # self.stop_loss_long()
                    self.take_profit_long()

                    self.id = True
                    self.isLong = True

                except:
                    self.id = None
                    self.isLong = False
                    self.isShort = False
                    print('Order Failed for long position')

            elif self.id != None and self.isShort:
                print('Short position close has been placed')

                while (self.check_position()):
                    self.exchange_conn.private_delete_order_all(
                        {"symbol": self.symbol})
                    self.close_short()
                    time.sleep(5)

                self.isLong = False
                self.isShort = False
                self.id = None

        elif latest_val['PSARs_0.06_0.6'] > 0 and latest_val['PSARr_0.06_0.6'] == 1:
            if self.id == None and df[4].iloc[-1] < d1 and self.isShort != True:

                try:
                    retries_order = 11

                    while self.check_position() != True and retries_order > 0:
                        self.exchange_conn.private_delete_order_all(
                            {"symbol": self.symbol})
                        time.sleep(1)
                        self.open_short()
                        self.open_long()
                        print('sell')
                        time.sleep(5)
                        retries_order -= 1
                        if retries_order == 1:
                            raise Exception
                    time.sleep(2)

                    # self.stop_loss_short()
                    self.take_profit_short()

                    self.id = True
                    self.isShort = True

                except:
                    self.isShort = False
                    self.id = None
                    self.isShort = False
                    print('Order Failed for short position')

            elif self.id != None and self.isLong:
                print('Long position close has been placed')

                while (self.check_position()):
                    self.exchange_conn.private_delete_order_all(
                        {"symbol": self.symbol})
                    self.close_long()
                    time.sleep(5)

                self.isShort = False
                self.isLong = False
                self.id = None

        print("App is running")
        time.sleep(15)

        x = self.check_position()
        print(x)
        if x == False:
            self.exchange_conn.private_delete_order_all({"symbol": self.symbol})
            self.id = None
            self.isLong = False
            self.isShort = False

        elif x == True:
            pnl_status, type_to_close = self.pnl_realised_profit()

            qty = float(self.exchange_conn.private_get_position(
                {"symbol": self.symbol})[0]['currentQty'])

            if qty < 0:
                self.isShort = True
                self.id = True

            elif qty > 0:
                self.isLong = True
                self.id = True

            else:
                self.id = None
                self.isLong = False
                self.isShort = False

            print(pnl_status, type_to_close)

            if pnl_status == True:
                if type_to_close == 'Buy':
                    retry_no = 50
                    while self.check_position() != False:
                        self.close_short()
                        time.sleep(5)
                        self.exchange_conn.private_delete_order_all({"symbol": self.symbol})
                        
                        print('close short')
                        retry_no -= 1

                        if retry_no == 1:
                            break

                elif type_to_close == 'Sell':
                    retry_no = 50
                    while self.check_position() != False:
                        self.exchange_conn.private_delete_order_all({"symbol": self.symbol})
                        self.close_long()
                        time.sleep(5)
                        print('close short')
                        retry_no -= 1
                        if retry_no == 1:
                            break

            # time.sleep(30)

        # return self.id,self.isLong,self.isShort
        return self.logic_exec(self.id, self.isLong, self.isShort)


class StreamlitApp:
    def __init__(self):
        self.is_running = False
        self.bot = None

    def run(self):

        bot = bitmex_trading_bot()
        bot.logic_exec()


app = Flask(__name__)
CORS(app)


@app.route('/')
def index():
    return render_template('index.html')


if __name__ == '__main__':

    retries = 5
    while retries > 0:
        running = False
        try:
            thread = threading.Thread(target=app.run, kwargs={
                'debug': False, 'host': '0.0.0.0', 'port': 8080})
            thread.start()

            if running != True:

                bot = StreamlitApp()
                bot.run()
                running = True

        except Exception as e:
            print(f"An error occurred: {e}")
            retries -= 1
            print(f"Retrying in 10 seconds... (Retry {retries}/5)")
            time.sleep(10)
