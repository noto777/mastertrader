import ib_insync
import asyncio
import typing
import datetime
import config.config as cfg
import utils.logger as logger_utils  # Import the logger utility

class IBConnection:
    def __init__(self):
        self.host = cfg.IB_HOST
        self.port = cfg.IB_PORT
        self.client_id = cfg.IB_CLIENT_ID
        self.ib: typing.Optional[ib_insync.IB] = None
        self.logger = logger_utils.get_logger(__name__)  # Use the new logger

    async def connect(self) -> bool:
        """Establish connection to Interactive Brokers TWS/Gateway"""
        try:
            self.ib = ib_insync.IB()
            await self.ib.connectAsync(
                host=self.host,
                port=self.port,
                clientId=self.client_id
            )
            self.logger.info("Successfully connected to IB")
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to IB: {str(e)}")
            return False

    async def disconnect(self):
        """Disconnect from IB"""
        if self.ib and self.ib.isConnected():
            self.ib.disconnect()
            self.logger.info("Disconnected from IB")

    def is_connected(self) -> bool:
        """Check if connected to IB"""
        return self.ib is not None and self.ib.isConnected() 