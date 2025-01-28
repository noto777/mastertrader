import yfinance as yf

# Download historical data for AAPL
data = yf.download('AAPL', start='2020-01-01', end='2025-01-01')
data.to_csv('AAPL.csv')