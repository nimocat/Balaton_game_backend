import os
import sys

# Ensure the directory containing alg.py is in the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
from alg import check_login_method


class TestCheckLoginMethod(unittest.TestCase):
    def test_type_1_valid_user_and_hash(self):
        data = {'user': {'id': 123}, 'hash': 'abc123'}
        self.assertEqual(check_login_method(data), 1)

    def test_type_2_valid_player_name_and_msg_id(self):
        data = {'player_name': 'JohnDoe', 'msg_id': '456'}
        self.assertEqual(check_login_method(data), 2)

    def test_type_0_invalid_data(self):
        data = {'user': 'not_a_dict', 'hash': 'abc123'}
        self.assertEqual(check_login_method(data), 0)

    def test_type_0_missing_user_id(self):
        data = {'user': {}, 'hash': 'abc123'}
        self.assertEqual(check_login_method(data), 0)

    def test_type_0_missing_hash(self):
        data = {'user': {'id': 123}}
        self.assertEqual(check_login_method(data), 0)

    def test_type_0_empty_data(self):
        data = {}
        self.assertEqual(check_login_method(data), 0)

    def test_type_0_missing_player_name(self):
        data = {'msg_id': '456'}
        self.assertEqual(check_login_method(data), 0)

    def test_type_0_missing_msg_id(self):
        data = {'player_name': 'JohnDoe'}
        self.assertEqual(check_login_method(data), 0)

if __name__ == '__main__':
    unittest.main()