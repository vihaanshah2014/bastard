# H.E.R.M.E.S. - High-frequency Execution and Risk Management Engine for Multi-asset Strategies
# Currently uses HERMES ML algo
import os
import numpy as np
import pandas as pd
import yfinance as yf
import warnings
import tensorflow as tf
from flask import Flask, request, jsonify
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Dropout, LSTM
import datetime as dt
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import json


# Suppressing unnecessary warnings
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=UserWarning, message='Starting a Matplotlib GUI outside of the main thread will likely fail.')

# Flask app definition
app = Flask(__name__)

# Define LSTM model structure
def create_model(input_shape):
    model = Sequential([
        LSTM(units=50, return_sequences=True, input_shape=input_shape),
        Dropout(0.2),
        LSTM(units=50, return_sequences=True),
        Dropout(0.2),
        LSTM(units=50),
        Dropout(0.2),
        Dense(units=1)
    ])
    model.compile(optimizer='adam', loss='mean_squared_error')
    return model

# Route for prediction
@app.route('/')
def predict():
    # Example hardcoded values for demonstration
    max_lookback_years = 8
    prediction_days = 60

    start_date = (datetime.now() - timedelta(days=prediction_days * 50)).strftime('%Y-%m-%d')
    eight_years_ago = (datetime.now() - timedelta(days=365 * max_lookback_years)).strftime('%Y-%m-%d')
    start_date = max(start_date, eight_years_ago)
    end_date = datetime.now().strftime('%Y-%m-%d')

    symbol = 'SPY'

    # Load and prepare data
    data = yf.download(symbol, start=start_date, end=end_date)
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled_data = scaler.fit_transform(data['Close'].values.reshape(-1,1))

    x_train = []
    y_train = []

    # Generating training data
    for x in range(prediction_days, len(scaled_data)):
        x_train.append(scaled_data[x-prediction_days:x, 0])
        y_train.append(scaled_data[x, 0])

    x_train, y_train = np.array(x_train), np.array(y_train)
    x_train = np.reshape(x_train, (x_train.shape[0], x_train.shape[1], 1))

    # Create, compile and train the LSTM model
    model = create_model((x_train.shape[1], 1))
    model.fit(x_train, y_train, epochs=2, batch_size=32)

    # Preparing test data
    test_start = dt.datetime.now() - dt.timedelta(days=30)
    test_end = dt.datetime.now()
    test_data = yf.download(symbol, start=test_start, end=test_end)
    actual_prices = test_data['Close'].values

    total_dataset = pd.concat((data['Close'], test_data['Close']), axis=0)

    model_inputs = total_dataset[len(total_dataset) - len(test_data) - prediction_days:].values
    model_inputs = model_inputs.reshape(-1, 1)
    model_inputs = scaler.transform(model_inputs)

    x_test = []

    # Generating test data
    for x in range(prediction_days, len(model_inputs)):
        x_test.append(model_inputs[x-prediction_days:x, 0])

    x_test = np.array(x_test)
    x_test = np.reshape(x_test, (x_test.shape[0], x_test.shape[1], 1))

    predicted_prices = model.predict(x_test)
    predicted_prices = scaler.inverse_transform(predicted_prices)

    # Calculate the accuracy of predictions
    actual_prices_trimmed = actual_prices[-len(predicted_prices):] # Ensure lengths match
    mape = np.mean(np.abs((actual_prices_trimmed - predicted_prices.flatten()) / actual_prices_trimmed)) * 100

    # Adjusting for output: Get the last predicted price as the next day's prediction
    predicted_price_next_day = float(predicted_prices[-1][0]) if predicted_prices.size > 0 else None

    # Convert the MAPE to a float as well
    accuracy_percentage = float(100 - mape)  # Ensure this is a native Python float

    prediction_date = dt.datetime.strptime(end_date, '%Y-%m-%d') + dt.timedelta(days=1)
    prediction_date_str = prediction_date.strftime('%Y-%m-%d')  # Convert to string for JSON serialization

    # Calculate the percent gain or loss
    actual_last_day_price = actual_prices[-1] if len(actual_prices) > 0 else None
    if actual_last_day_price and predicted_price_next_day:
        percent_change = ((predicted_price_next_day - actual_last_day_price) / actual_last_day_price) * 100
    else:
        percent_change = None  # In case data is missing

    # Output the required information as an array
    output = {
        "Symbol": symbol,  # Stock ticker
        "Start Date": start_date,  # Start date for the data used in prediction
        "End Date": end_date,  # End date for the data used in prediction
        "Prediction Date": prediction_date_str,  # The day for which the prediction is made
        "Predicted Price for Next Day": predicted_price_next_day,  # Predicted Price for the next day
        "Accuracy Percentage": accuracy_percentage,  # Percent Accuracy of the model on trained data        
        "Percent Change from Last Day": percent_change,  # Percent gain or loss from yesterday's prediction
        "Riches do not exhilarate us so much with their possession as they torment us with their loss.": "Epicurus"  # Any custom message you want to include
    }

    response = app.response_class(
        response=json.dumps(output, indent=4),
        status=200,
        mimetype='application/json'
    )
    return response

# Running the Flask app
if __name__ == '__main__':
    app.run(debug=True)