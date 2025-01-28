import sys
import os

# Add the project root to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Debugging sys.path
print("Updated sys.path:")
print("\n".join(sys.path))

# frontend/gradio_frontend.py
import asyncio
import threading
from core.database import Database
from core.order_manager import OrderManager
from core.portfolio_manager import PortfolioManager
from core.signal_generator import SignalGenerator
from utils.logger import setup_logger
import gradio as gr
import config.config as cfg
from ib_insync import IB, util
import pandas as pd
import plotly.express as px




# Imports
from core.database import Database
from core.order_manager import OrderManager


logger = setup_logger(__name__)

# Initialize Backend Components
db = Database()  # Initialize the database

# Set up Interactive Brokers (IB) connection
ib = IB()
try:
    ib.connect(cfg.IB_HOST, cfg.IB_PORT, cfg.IB_CLIENT_ID)
    logger.info("Connected to Interactive Brokers (IB).")
except Exception as e:
    logger.error(f"Failed to connect to IB: {e}")
    sys.exit(1)  # Exit the script if the connection fails

# Initialize components
order_manager = OrderManager(ib=ib, db=db)  # Order manager needs both IB and Database
portfolio_manager = PortfolioManager(ib=ib, db=db)  # Portfolio manager needs both IB and Database
signal_generator = SignalGenerator(ib=ib, db=db)  # Pass IB and Database to SignalGenerator



# Trading Control
trading_tasks = {}
shutdown_event = asyncio.Event()


async def start_trading():
    """Start trading loops."""
    if not trading_tasks:
        trading_tasks['signal_processing'] = asyncio.create_task(process_signals())
        trading_tasks['data_refresh'] = asyncio.create_task(refresh_data())
        logger.info("Trading tasks started.")
        return "Trading started."
    return "Trading is already running."


async def stop_trading():
    """Stop all trading loops."""
    shutdown_event.set()
    for task_name, task in trading_tasks.items():
        task.cancel()
        logger.info(f"{task_name} task cancelled.")
    trading_tasks.clear()
    logger.info("All trading tasks stopped.")
    return "Trading stopped."


async def process_signals():
    """Process trading signals."""
    while not shutdown_event.is_set():
        try:
            symbols = db.get_all_symbols()
            for symbol in symbols:
                signal_generator.generate_signals(symbol)
            await asyncio.sleep(5)  # Example interval
        except Exception as e:
            logger.error(f"Error processing signals: {e}")


async def refresh_data():
    """Refresh trading data periodically."""
    while not shutdown_event.is_set():
        try:
            await portfolio_manager.rebalance_portfolio()
            await asyncio.sleep(30)  # Example interval
        except Exception as e:
            logger.error(f"Error refreshing data: {e}")


# UI Functions
def get_overview():
    """Fetch account overview."""
    try:
        account_value = db.get_account_value()
        positions = db.get_positions_summary()
        return f"Account Value: ${account_value:,.2f}\n\nPositions:\n{positions}"
    except Exception as e:
        logger.error(f"Error fetching overview: {e}")
        return "Failed to fetch overview."


def get_orders():
    """Fetch all orders."""
    try:
        orders = db.get_all_orders()
        if not orders:
            return "No orders found."
        return "\n".join([f"ID: {o['order_id']} | {o['symbol']} | {o['order_type']} | {o['status']}" for o in orders])
    except Exception as e:
        logger.error(f"Error fetching orders: {e}")
        return "Failed to fetch orders."


def get_positions():
    """Fetch positions."""
    try:
        positions = db.get_all_positions()
        if not positions:
            return "No positions found."
        return "\n".join([f"Symbol: {p['symbol']} | Qty: {p['quantity']} | Avg Price: ${p['avg_price']:.2f}" for p in positions])
    except Exception as e:
        logger.error(f"Error fetching positions: {e}")
        return "Failed to fetch positions."


def plot_trades(symbol=None):
    """Plot trades for the given symbol."""
    try:
        trades = db.get_all_trades()
        if not trades:
            return "No trades to plot."
        df = pd.DataFrame(trades)
        if symbol:
            df = df[df['symbol'] == symbol]
        fig = px.scatter(df, x='trade_date', y='price', color='trade_type', title=f"Trades for {symbol or 'all symbols'}")
        return fig
    except Exception as e:
        logger.error(f"Error plotting trades: {e}")
        return "Failed to generate plot."


def launch_gradio():
    """Launch the Gradio UI."""
    with gr.Blocks() as demo:
        with gr.Tab("Overview"):
            overview = gr.Textbox(label="Overview", interactive=False)
            overview_button = gr.Button("Load Overview")
            overview_button.click(get_overview, inputs=None, outputs=overview)

        with gr.Tab("Orders"):
            orders_view = gr.Textbox(label="Orders", interactive=False)
            orders_button = gr.Button("Load Orders")
            orders_button.click(get_orders, inputs=None, outputs=orders_view)

        with gr.Tab("Positions"):
            positions_view = gr.Textbox(label="Positions", interactive=False)
            positions_button = gr.Button("Load Positions")
            positions_button.click(get_positions, inputs=None, outputs=positions_view)

        with gr.Tab("Trades Plot"):
            symbol_input = gr.Textbox(label="Symbol (optional)")
            plot_button = gr.Button("Plot Trades")
            trade_plot = gr.Plot()
            plot_button.click(plot_trades, inputs=symbol_input, outputs=trade_plot)

        with gr.Tab("Control Panel"):
            start_button = gr.Button("Start Trading")
            stop_button = gr.Button("Stop Trading")
            start_output = gr.Textbox(label="Start Output", interactive=False)
            stop_output = gr.Textbox(label="Stop Output", interactive=False)

            start_button.click(lambda: asyncio.run(start_trading()), inputs=None, outputs=start_output)
            stop_button.click(lambda: asyncio.run(stop_trading()), inputs=None, outputs=stop_output)

    return demo


if __name__ == "__main__":
    logger.info("Launching Gradio Frontend.")
    demo = launch_gradio()
    demo.launch()
