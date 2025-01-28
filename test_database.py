import unittest
from core.database import Database

class TestDatabase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = Database()
        cls.db.setup_database()

    def setUp(self):
        """Clear tables before each test."""
        self.db.execute_query("DELETE FROM signals")

    def tearDown(self):
        """Clean up after each test."""
        self.db.execute_query("DELETE FROM signals")

    def test_setup_database(self):
        """Verify tables are created successfully."""
        query = "SELECT name FROM sqlite_master WHERE type='table';"
        tables = [row['name'] for row in self.db.fetch_all(query)]
        self.assertIn('signals', tables)
        self.assertIn('orders', tables)

    def test_record_signal(self):
        """Test recording a signal."""
        self.db.record_signal('AAPL', 'BUY', rsi_value=25.0, signal_strength=1.0, gap_percent=2.5)
        query = "SELECT * FROM signals WHERE symbol = 'AAPL'"
        results = self.db.fetch_all(query)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['symbol'], 'AAPL')
        self.assertEqual(results[0]['signal_type'], 'BUY')

    def test_fetch_all(self):
        """Test fetch_all method."""
        self.db.record_signal('AAPL', 'BUY', rsi_value=25.0, signal_strength=1.0, gap_percent=2.5)
        query = "SELECT * FROM signals WHERE symbol = 'AAPL'"
        results = self.db.fetch_all(query)
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0]['symbol'], 'AAPL')

    def test_backup_database(self):
        """Test backing up the database."""
        result = self.db.backup_database()
        self.assertTrue(result)

    def test_execute_query_error(self):
        """Test error handling in execute_query."""
        with self.assertRaises(Exception):
            self.db.execute_query("INVALID SQL")

    @classmethod
    def tearDownClass(cls):
        cls.db.connection.close()

if __name__ == "__main__":
    unittest.main()
