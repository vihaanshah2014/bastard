# B.A.S.T.A.R.D - Boldly Analyzing and Strategizing Trade Algorithm for Radical Dividends


from lumibot.brokers import Alpaca
from lumibot.backtesting import YahooDataBacktesting
from lumibot.strategies.strategy import Strategy
from lumibot.traders import Trader
import pandas as pd
import pytz
import yfinance as yf
from datetime import datetime

# news api
from alpaca_trade_api import REST
from timedelta import Timedelta
from datetime import timedelta  # Import timedelta from datetime module
import numpy as np
from pandas_datareader import data as web
import os



# importing AI
from finbert_utils import estimate_sentiment


API_KEY = "PKPQ89WRWLU05IA5JK52"
API_SECRET = "4eKdigiTzaQNoKsgPnG6G5dlVjzAz91f9dKxTZBJ"
os.environ["ALPHAVANTAGE_API_KEY"] = "VGLCCAJRPMIG9LV3"
BASE_URL = "https://paper-api.alpaca.markets"

ALPACA_CREDS = {
    "API_KEY": API_KEY,
    "API_SECRET": API_SECRET,
    "PAPER": True
}

class MLTrader(Strategy):
    def initialize(self, symbol:str="SPY", cash_at_risk:float=.5):
        self.symbol = symbol
        self.sleeptime = "24H"
        self.last_trade = None
        self.cash_at_risk = cash_at_risk
        self.api = REST(base_url=BASE_URL, key_id=API_KEY, secret_key=API_SECRET)



    def position_sizing(self):
        cash = self.get_cash()
        last_price = self.get_last_price(self.symbol)
        quantity = round(cash * self.cash_at_risk / last_price)

        while quantity * last_price > cash:
            quantity -= 1

        if quantity * last_price > cash:
            quantity = 0

        return cash, last_price, quantity



    
    def get_dates(self):
        today = self.get_datetime()
        three_days_prior = today - Timedelta(days=3)
        return today.strftime('%Y-%m-%d'), three_days_prior.strftime('%Y-%m-%d')

    
    def get_sentiment(self):
        today, three_days_prior = self.get_dates()
        news = self.api.get_news(symbol=self.symbol, start=three_days_prior, end=today)

        news = [ev.__dict__["_raw"]["headline"] for ev in news]

        probability, sentiment = estimate_sentiment(news)
        return probability, sentiment



    def risk_values(self, probability, buy=True):
        base_cash = 100000  # Set the base cash value
        cash = self.get_cash()

        asset_volatility = self.calculate_volatility(self.symbol, lookback=14)
        
        # Check if asset_volatility is None, and handle the case appropriately
        if asset_volatility is None:
            print("Unable to calculate volatility. Skipping trade.")
            asset_volatility = 0.1

        risk_tolerance = 0.02  # a constant that you can adjust based on a user's risk tolerance
        volatility_adjustment_factor = asset_volatility * risk_tolerance

        if cash < base_cash:
            adjustment_factor = max(0.5, cash / base_cash - volatility_adjustment_factor)
        else:
            adjustment_factor = 1 + volatility_adjustment_factor

        if buy:
            min_value = 0.95 * adjustment_factor
            max_value = 1.20 * adjustment_factor
        else:
            min_value = 0.8 * adjustment_factor
            max_value = 1.05 * adjustment_factor

        if probability < 0.5:
            min_value *= 0.9
            max_value *= 0.9
        elif probability > 0.7:
            min_value *= 1.1
            max_value *= 1.1

        return min_value, max_value

    

    def calculate_volatility(self, symbol, lookback=14):
        f = web.DataReader(symbol, "av-daily", start=datetime(2017, 2, 9),
                        end=datetime(2017, 5, 24),
                        api_key=os.getenv('ALPHAVANTAGE_API_KEY'))
        # calculate daily returns
        f['return'] = f['close'].pct_change()
        # calculate rolling standard deviation of returns
        f['volatility'] = f['return'].rolling(window=lookback).std()
        # Latest Volatility as a decimal
        volatility = f['volatility'].iloc[-1]
        
        return volatility
    



    



    def get_probability_value(self):
        base_cash = 100000  # Set the base cash value
        cash_reserve_percentage = self.get_cash() / base_cash

        # Customize this formula based on your risk strategy
        probability_value = 0.8 + 0.05 * cash_reserve_percentage

        # Ensure the probability value is within a reasonable range
        probability_value = max(0.7, min(0.9, probability_value))

        return probability_value
    
    


    def calculate_moving_average(self, symbol: str, days: int):
        end_date = self.get_datetime()
        try:
            start_date = end_date - pd.DateOffset(days=days)
        except Exception as e:
            print(f"Error occurred while calculating start date: {e}")
            start_date = end_date - pd.Timedelta(days=days)

        data = yf.download(symbol, start=start_date, end=end_date)
        close_prices = data['Close']
        moving_average = close_prices.rolling(window=days).mean().iloc[-1]

        return moving_average







    def on_trading_iteration(self): 
        CASH_MINIMUM = 1000
        probability_value = self.get_probability_value()
        cash, last_price, quantity = self.position_sizing()
        # moving_average = self.calculate_moving_average(self.symbol, 50)
        moving_average = last_price



        probability, sentiment = self.get_sentiment()

        if cash > last_price and cash > CASH_MINIMUM:
            if last_price <= moving_average and sentiment == "positive" and probability > probability_value:
                min_val, max_val = self.risk_values(probability=probability, buy=True)
                if self.last_trade == "sell":
                    self.sell_all()
                order = self.create_order(
                    self.symbol,
                    quantity,
                    "buy",
                    type="bracket",
                    take_profit_price=last_price * max_val,
                    stop_loss_price=last_price * min_val
                )
                self.submit_order(order)
                self.last_trade = "buy"
            elif last_price >= moving_average and sentiment == "negative" and probability > probability_value: 
                min_val, max_val = self.risk_values(probability=probability, buy=False)
                if self.last_trade == "buy":
                        self.sell_all()
                order = self.create_order(
                    self.symbol,
                    quantity,
                    "sell",
                    type="bracket",
                    take_profit_price=last_price * min_val,
                    stop_loss_price=last_price * max_val
                )
                self.submit_order(order)
                self.last_trade = "sell"


start_date = datetime(2024,1,15)
end_date = datetime(2024,1,24)
broker = Alpaca(ALPACA_CREDS)

strategy = MLTrader(name='bastardv1', 
                    broker = broker,
                    parameters={"symbol":"SPY",
                    "cash_at_risk":.5})
strategy.backtest(
    YahooDataBacktesting,
    start_date,
    end_date,
    parameters={"symbol":"SPY"}
)