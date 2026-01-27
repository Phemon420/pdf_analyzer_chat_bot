import sys
import unittest
from unittest.mock import MagicMock, patch
import os

# Simplified test that doesn't rely on asyncio for the core logic we want to test
# We want to verify how the query string is built from the parameters

def test_query_logic(filename=None, mime_type=None, raw_query=None):
    query_parts = []
    if filename:
        safe_filename = filename.replace("'", "\\'")
        query_parts.append(f"name contains '{safe_filename}'")
    if mime_type:
        query_parts.append(f"mimeType = '{mime_type}'")
    if raw_query:
        query_parts.append(raw_query)
    final_query = " and ".join(query_parts) if query_parts else None
    return final_query

class TestDriveQueryLogic(unittest.TestCase):
    def test_basic_query(self):
        res = test_query_logic(filename="OmPlacementResume (5)", mime_type="application/pdf")
        self.assertEqual(res, "name contains 'OmPlacementResume (5)' and mimeType = 'application/pdf'")
        
    def test_quote_escaping(self):
        res = test_query_logic(filename="O'Connor's Resume")
        self.assertEqual(res, "name contains 'O\\'Connor\\'s Resume'")
        
if __name__ == '__main__':
    print("Starting tests...")
    unittest.main()
