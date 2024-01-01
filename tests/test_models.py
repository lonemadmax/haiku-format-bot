#
# Copyright 2023 Haiku, Inc. All rights reserved.
# Distributed under the terms of the MIT License.
#
# Authors:
#  Niels Sascha Reedijk, niels.reedijk@gmail.com
#
import os
import unittest

from formatchecker.models import FormatSegment, Segment, ReformatType, File


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

    def test_equality(self):
        self.assertEqual(Segment(100,200), Segment(100,200))
        self.assertNotEqual(Segment(100, 200), Segment(100, None))


class FormatSegmentTest(unittest.TestCase):
    # Test contents
    _content = ["line1\n", "line2\n"]

    def test_reformat_type(self):
        # Valid insert segment
        f = FormatSegment(15, None, self._content)
        self.assertEqual(f.start, 15)
        self.assertIsNone(f.end)
        self.assertEqual(f.formatted_content, self._content)
        self.assertEqual(f.reformat_type, ReformatType.INSERTION)

        # Invalid insert segment
        self.assertRaises(ValueError, FormatSegment, 15, None, [])

        # Valid modification segment
        f = FormatSegment(15, 20, self._content)
        self.assertEqual(f.start, 15)
        self.assertEqual(f.end, 20)
        self.assertEqual(f.formatted_content, self._content)
        self.assertEqual(f.reformat_type, ReformatType.MODIFICATION)

        # Valid deletion segment
        f = FormatSegment(15,20, [])
        self.assertEqual(f.start, 15)
        self.assertEqual(f.end, 20)
        self.assertEqual(f.formatted_content, [])
        self.assertEqual(f.reformat_type, ReformatType.DELETION)

    def test_equality(self):
        contents = ["line1"]
        self.assertEqual(FormatSegment(100,200, self._content), FormatSegment(100,200, self._content))
        self.assertNotEqual(FormatSegment(100, 200, self._content), FormatSegment(100, 200, []))


class FileTest(unittest.TestCase):
    # Static data
    _patch_segments = [Segment(25, 25), Segment(37,49), Segment(51, 52),
                         Segment(61, 61), Segment(83, 83), Segment(85, 85)]

    @classmethod
    def setUpClass(cls):
        data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
        with open(os.path.join(data_path, "test_models_file_base")) as f:
            cls._base_contents = f.readlines()
        with open(os.path.join(data_path, "test_models_file_patch")) as f:
            cls._patch_contents = f.readlines()

    def test_initialization(self):
        # Helper functions to check that properties raise exceptions
        def get_patch_segments(f: File) -> list[Segment]:
            return f.patch_segments

        def get_format_segments(f: File) -> list[Segment]:
            return f.format_segments

        # Create object with no content
        f = File("filename")
        self.assertIsNone(f.base_contents)
        self.assertIsNone(f.patch_contents)
        self.assertIsNone(f.formatted_contents)
        self.assertRaises(RuntimeError, get_patch_segments, f)
        self.assertRaises(RuntimeError, get_format_segments, f)

        # Create object with only base contents
        f = File("filename", self._base_contents)
        self.assertEqual(f.base_contents, self._base_contents)
        self.assertIsNone(f.patch_contents)
        self.assertIsNone(f.formatted_contents)
        self.assertRaises(RuntimeError, get_patch_segments, f)
        self.assertRaises(RuntimeError, get_format_segments, f)

        # Create object with only patched contents
        f = File("filename", patch=self._patch_contents)
        self.assertIsNone(f.base_contents)
        self.assertEqual(f.patch_contents, self._patch_contents)
        self.assertIsNone(f.formatted_contents)
        self.assertRaises(RuntimeError, get_patch_segments, f)
        self.assertRaises(RuntimeError, get_format_segments, f)

        # Create object with base and patch contents
        f = File("filename", self._base_contents, self._patch_contents)
        self.assertEqual(f.base_contents, self._base_contents)
        self.assertEqual(f.patch_contents, self._patch_contents)
        self.assertIsNone(f.formatted_contents)
        self.assertEqual(f.patch_segments, self._patch_segments)
        self.assertRaises(RuntimeError, get_format_segments, f)
