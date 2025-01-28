import gradio as gr
import pandas as pd
from ib_insync import Stock
import config.config as cfg
import core.order_manager as order_manager
import core.portfolio_manager as portfolio_manager
import core.connection as connection

# Establish connection using connection.py
ib_connection = connection.IBConnection()
ib = ib_connection.connect()

# Initialize managers
order_mgr = order_manager.OrderManager(ib)
portfolio_mgr = portfolio_manager.PortfolioManager(ib)

def fetch_data():
    # Fetch current positions using PortfolioManager
    positions = portfolio_mgr.get_positions()
    current_holdings = pd.DataFrame([{
        'Symbol': pos.contract.symbol,
        'Shares': pos.position,
        'PnL': pos.unrealizedPNL,
        'Type': 'Core' if pos.contract.symbol in cfg.CORE_SYMBOLS else 'Trading'
    } for pos in positions])

    # Fetch market data for potential trades using OrderManager
    potential_trades = []
    for symbol in cfg.CORE_SYMBOLS + cfg.TRADING_SYMBOLS:
        contract = Stock(symbol, 'SMART', 'USD')
        market_data = ib.reqMktData(contract, '', False, False)
        ib.sleep(1)  # Allow time for data to be fetched
        potential_trades.append({
            'Symbol': symbol,
            'Action': 'Buy' if market_data.last < 150 else 'Sell',  # Example logic
            'Target Price': market_data.last
        })
    potential_trades_df = pd.DataFrame(potential_trades)

    return potential_trades_df, current_holdings

# Create Gradio interface
iface = gr.Interface(
    fn=fetch_data,
    inputs=[],
    outputs=[
        gr.outputs.Dataframe(label="Potential Trades"),
        gr.outputs.Dataframe(label="Current Holdings")
    ],
    live=True
)

# Launch the interface
iface.launch()