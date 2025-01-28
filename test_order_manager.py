import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from core.order_manager import OrderManager
from core.database import Database


class TestOrderManager(unittest.TestCase):
    def setUp(self):
        self.mock_ib = MagicMock()
        self.mock_db = MagicMock(spec=Database)
        self.om = OrderManager(ib=self.mock_ib, db=self.mock_db)

    @patch('core.order_manager.util.ib.qualifyContracts')
    def test_place_limit_order_success(self, mock_qualifyContracts):
        mock_qualifyContracts.return_value = [MagicMock()]  # Mock contract qualification
        self.mock_ib.placeOrder = MagicMock()  # Mock IB's placeOrder
        self.mock_ib.placeOrder.return_value.isDone.return_value = True
        self.mock_ib.placeOrder.return_value.orderStatus.status = 'Filled'

        # Run the test
        order_result = asyncio.run(self.om.place_limit_order("AAPL", "BUY", 100, 150.0))

        # Validate behavior
        self.assertTrue(order_result)
        self.mock_ib.placeOrder.assert_called_once()

    def test_get_order_status(self):
        # Mock database response
        self.mock_db.get_order.return_value = {'order_id': 1, 'status': 'PENDING'}
        order_status = self.om.get_order_status(1)

        # Validate behavior
        self.assertEqual(order_status['status'], 'PENDING')
        self.mock_db.get_order.assert_called_once_with(1)

    def test_cancel_order(self):
        # Mock database response and IB cancellation
        self.mock_db.get_order.return_value = {'order_id': 1, 'status': 'PENDING'}
        self.mock_ib.cancelOrder = MagicMock()

        # Run the test
        result = self.om.cancel_order(1)

        # Validate behavior
        self.assertTrue(result)
        self.mock_ib.cancelOrder.assert_called_once_with(1)
        self.mock_db.update_order_status.assert_called_once_with(1, 'CANCELLED')

    def test_get_active_orders(self):
        # Mock database response
        self.mock_db.get_active_orders.return_value = [
            {'order_id': 1, 'symbol': 'AAPL', 'status': 'PENDING'},
            {'order_id': 2, 'symbol': 'TSLA', 'status': 'PENDING'}
        ]
        active_orders = self.om.get_active_orders()

        # Validate behavior
        self.assertEqual(len(active_orders), 2)
        self.mock_db.get_active_orders.assert_called_once()


if __name__ == '__main__':
    unittest.main()
