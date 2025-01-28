import sys
import os
import traceback
from datetime import datetime

# Adjust the Python path to include the project root
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir))
sys.path.append(project_root)

from core.database import Database
from utils.logger import setup_logging, get_logger

def test_error_logging():
    setup_logging()
    logger = get_logger(__name__)
    db = Database()
    
    try:
        # Test 1: Log a simple error
        logger.info("Test 1: Logging a simple error")
        success = db.log_error(
            error_type="TEST_ERROR",
            error_message="This is a test error",
            stack_trace=None
        )
        print(f"Test 1 - Log simple error: {'Success' if success else 'Failed'}")

        # Test 2: Log an error with stack trace
        logger.info("Test 2: Logging error with stack trace")
        try:
            # Deliberately cause an error
            result = 1 / 0
        except Exception as e:
            stack_trace = traceback.format_exc()
            success = db.log_error(
                error_type="DIVISION_ERROR",
                error_message=str(e),
                stack_trace=stack_trace
            )
        print(f"Test 2 - Log error with stack trace: {'Success' if success else 'Failed'}")

        # Test 3: Retrieve recent errors
        logger.info("Test 3: Retrieving recent errors")
        recent_errors = db.get_recent_errors(limit=5)
        print("\nRecent Errors:")
        for error in recent_errors:
            print(f"\nError Type: {error['error_type']}")
            print(f"Message: {error['error_message']}")
            print(f"Time: {error['created_at']}")
            if error['stack_trace']:
                print(f"Stack Trace: {error['stack_trace'][:100]}...")

        # Test 4: Clear old errors
        logger.info("Test 4: Clearing old errors")
        success = db.clear_old_errors(days=7)
        print(f"\nTest 4 - Clear old errors: {'Success' if success else 'Failed'}")

        # Test 5: Verify error count
        logger.info("Test 5: Verifying error count")
        final_errors = db.get_recent_errors()
        print(f"Current error count in database: {len(final_errors)}")

    except Exception as e:
        logger.error(f"Error during testing: {str(e)}")
        print(f"Testing failed: {str(e)}")

if __name__ == "__main__":
    test_error_logging() 