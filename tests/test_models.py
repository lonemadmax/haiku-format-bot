#
# Copyright 2023 Haiku, Inc. All rights reserved.
# Distributed under the terms of the MIT License.
#
# Authors:
#  Niels Sascha Reedijk, niels.reedijk@gmail.com
#

import unittest

from formatchecker.models import Segment


class SegmentTest(unittest.TestCase):
    def test_input(self):
        # Test invalid start (start < 1)
        self.assertRaises(ValueError, Segment, 0,None)
        # Test invalid end (end < 1)
        self.assertRaises(ValueError, Segment, 1,0)
        # Test invalid range (end < start)
        self.assertRaises(ValueError, Segment, 50,45)

        # Test valid input
        s = Segment(1, None)
        self.assertEqual(s.start, 1)
        self.assertEqual(s.end, None)

        s = Segment(15, 30)
        self.assertEqual(s.start, 15)
        self.assertEqual(s.end, 30)

    def test_format_range(self):
        # Valid range
        s = Segment(1,5)
        self.assertEqual(s.format_range(), "1:5")

        # Invalid range
        s = Segment(1, None)
        self.assertRaises(ValueError, s.format_range)
