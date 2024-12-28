#plotting the two
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

def get_dow_jones_data(symbol):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=10000)
    
    ticker = yf.Ticker(symbol)
    data = ticker.history(start=start_date, end=end_date)
    
    return data

def process_data(data):
    dates = data.index.to_list()
    close_prices = data['Close'].to_list()
    volatility = (data['High'] - data['Low']).to_list()

    return dates, close_prices, volatility

def plot_dow_jones_comparison(dju_dates, dju_prices, dju_volatility, dji_dates, dji_prices):
    fig, ax1 = plt.subplots(figsize=(14, 8))
    
    # Plot the DJU closing prices as a blue line
    ax1.plot(dju_dates, dju_prices, label='Dow Jones Utility Average (DJU)', color='blue', linewidth=2)
    
    # Plot the DJI closing prices as a green line
    ax1.plot(dji_dates, dji_prices, label='Dow Jones Industrial Average (DJI)', color='green', linewidth=2)
    
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Price (USD)', color='black')
    ax1.tick_params(axis='y', labelcolor='black')
    
    # Create a second y-axis for volatility
    ax2 = ax1.twinx()
    ax2.fill_between(dju_dates, dju_volatility, alpha=0.3, color='red', label='DJU Daily Volatility')
    ax2.set_ylabel('DJU Daily Volatility (USD)', color='red')
    ax2.tick_params(axis='y', labelcolor='red')
    
    plt.title('Dow Jones Utility Average vs Industrial Average: Prices and DJU Volatility (Last 6 Months)')
    fig.legend(loc='upper left', bbox_to_anchor=(0.1, 1), bbox_transform=ax1.transAxes)
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()

def main():
    # Fetch and process Dow Jones Utility Average data
    dju_data = get_dow_jones_data("^DJU")
    dji_data = get_dow_jones_data("^DJI")
    
    if not dju_data.empty and not dji_data.empty:
        dju_dates, dju_prices, dju_volatility = process_data(dju_data)
        dji_dates, dji_prices, _ = process_data(dji_data)
        
        # Normalize prices to start at 100 for easier comparison
        dju_prices_norm = [price / dju_prices[0] * 100 for price in dju_prices]
        dji_prices_norm = [price / dji_prices[0] * 100 for price in dji_prices]
        
        plot_dow_jones_comparison(dju_dates, dju_prices_norm, dju_volatility, dji_dates, dji_prices_norm)
    else:
        print("Error: No data fetched")

if __name__ == "__main__":
    main()