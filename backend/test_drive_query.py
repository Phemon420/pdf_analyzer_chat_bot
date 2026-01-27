import sys
import unittest
from unittest.mock import MagicMock, patch
import asyncio
import os

# Add the backend directory to sys.path so we can import modules from it
backend_path = os.path.dirname(os.path.abspath(__file__))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# Mocking the imports that would fail without full setup
sys.modules['sqlalchemy.orm'] = MagicMock()
sys.modules['google.oauth2.credentials'] = MagicMock()
sys.modules['google.auth.transport.requests'] = MagicMock()
sys.modules['google.auth.exceptions'] = MagicMock()
sys.modules['googleapiclient.discovery'] = MagicMock()
sys.modules['googleapiclient.http'] = MagicMock()
sys.modules['models'] = MagicMock()
sys.modules['models.google_token'] = MagicMock()

# Import the function to test from services
from services.google_services import list_drive_files

class TestDriveQuery(unittest.TestCase):
    @patch('services.google_services.get_service')
    def test_query_construction(self, mock_get_service):
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        
        # Test Case 1: Filename and mime_type
        params = {
            "filename": "OmPlacementResume (5)",
            "mime_type": "application/pdf"
        }
        
        # Run async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(list_drive_files(MagicMock(), 1, params))
        finally:
            loop.close()
        
        # Check the 'q' parameter passed to files().list()
        expected_query = "name = 'OmPlacementResume (5)' and mimeType = 'application/pdf'"
        
        # Verify it was called correctly
        args, kwargs = mock_service.files().list.call_args
        self.assertEqual(kwargs.get('q'), expected_query)

    @patch('services.google_services.get_service')
    def test_query_with_quotes(self, mock_get_service):
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        
        # Test Case 2: Filename with single quote
        params = {
            "filename": "O'Connor's Resume"
        }
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(list_drive_files(MagicMock(), 1, params))
        finally:
            loop.close()
            
        expected_query = "name = 'O\\'Connor\\'s Resume'"
        args, kwargs = mock_service.files().list.call_args
        self.assertEqual(kwargs.get('q'), expected_query)

if __name__ == '__main__':
    unittest.main()
