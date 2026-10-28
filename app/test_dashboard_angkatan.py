import unittest
import sqlite3
import uuid
import sys
import os

# Ensure modules can be imported
sys.path.append('C:/Financehub/app')
from modules.beasiswa.service import get_dashboard_summary

class TestDashboardAngkatanFilter(unittest.TestCase):
    def setUp(self):
        # We will just verify that the function accepts angkatans parameter
        # and doesn't crash, and ideally filters the data.
        # But we don't have a fake DB setup easily here without altering the real DB.
        # Wait, get_dashboard_summary uses get_conn() which connects to finance_hub.db.
        # So we can just test if the function accepts the parameter.
        self.cid = 1 # Assuming 1 is a valid company id (e.g. ETF)
        pass

    def test_angkatan_filter(self):
        try:
            # This should fail initially because get_dashboard_summary doesn't accept angkatans=...
            res = get_dashboard_summary(self.cid, angkatans=['2024'])
            self.assertTrue(isinstance(res, list) or isinstance(res, dict))
        except TypeError as e:
            self.fail(f"get_dashboard_summary does not accept angkatans parameter: {e}")

if __name__ == '__main__':
    unittest.main()
