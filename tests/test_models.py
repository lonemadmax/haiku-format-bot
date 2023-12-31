#
# Copyright 2023 Haiku, Inc. All rights reserved.
# Distributed under the terms of the MIT License.
#
# Authors:
#  Niels Sascha Reedijk, niels.reedijk@gmail.com
#

import unittest

from formatchecker.models import FormatSegment, Segment, ReformatType


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


class FormatSegmentTest(unittest.TestCase):
    def test_reformat_type(self):
        content = ["line1\n", "line2\n"]

        # Valid insert segment
        f = FormatSegment(15, None, content)
        self.assertEqual(f.start, 15)
        self.assertIsNone(f.end)
        self.assertEqual(f.formatted_content, content)
        self.assertEqual(f.reformat_type, ReformatType.INSERTION)

        # Invalid insert segment
        self.assertRaises(ValueError, FormatSegment, 15, None, [])

        # Valid modification segment
        f = FormatSegment(15, 20, content)
        self.assertEqual(f.start, 15)
        self.assertEqual(f.end, 20)
        self.assertEqual(f.formatted_content, content)
        self.assertEqual(f.reformat_type, ReformatType.MODIFICATION)

        # Valid deletion segment
        f = FormatSegment(15,20, [])
        self.assertEqual(f.start, 15)
        self.assertEqual(f.end, 20)
        self.assertEqual(f.formatted_content, [])
        self.assertEqual(f.reformat_type, ReformatType.DELETION)
