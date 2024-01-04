#
# Copyright 2023-2024 Haiku, Inc. All rights reserved.
# Distributed under the terms of the MIT License.
#
# Authors:
#  Niels Sascha Reedijk, niels.reedijk@gmail.com
#
import json
import os
import unittest

from formatchecker.gerrit import Context


def context_get_mock(self, url, params):
    data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    if url == "changes/" and params is None:
        # This is the get operation to check if the Gerrit URL is valid
        return
    elif url == "changes/" and "change:5692" in params.values():
        with open(os.path.join(data_path, "test_gerrit_get_change.json")) as f:
            return json.load(f)
    elif url == "changes/" and "change:19000" in params.values():
        return []
    raise ValueError("Input URL is not mocked")


class ContextTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Context._get = context_get_mock
        cls._context = Context("https://test-gerrit/")

    def test_get_change_id_from_number(self):
        self.assertEqual(self._context.get_change_id_from_number(5692),
                         "haiku~dev%2Fnetservices~I0dadd1dfd3fb36256bd6f4a2530dbbe12afefce5")
        self.assertRaises(ValueError, self._context.get_change_id_from_number, 19000)


if __name__ == '__main__':
    unittest.main()
