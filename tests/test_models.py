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

    # Helpers
    @classmethod
    def get_patch_segments(cls, f: File) -> list[Segment]:
        return f.patch_segments

    @classmethod
    def get_format_segments(cls, f: File) -> list[Segment]:
        return f.format_segments

    @classmethod
    def setUpClass(cls):
        data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
        with open(os.path.join(data_path, "test_models_file_base")) as f:
            cls._base_contents = f.readlines()
        with open(os.path.join(data_path, "test_models_file_patch")) as f:
            cls._patch_contents = f.readlines()
        with open(os.path.join(data_path, "test_models_file_formatted")) as f:
            cls._formatted_contents = f.readlines()
        # set up the format segments
        cls._format_segments = [
            FormatSegment(25, 25, cls._formatted_contents[24:25]),
            FormatSegment(37, 49, cls._formatted_contents[36:48]),
            FormatSegment(51, 52, cls._formatted_contents[49:52]),
            FormatSegment(88, 89, []),
            FormatSegment(95, None, cls._formatted_contents[93:95])
        ]

    def test_initialization(self):
        # Helper functions to check that properties raise exceptions

        # Create object with no content
        f = File("filename")
        self.assertIsNone(f.base_contents)
        self.assertIsNone(f.patch_contents)
        self.assertIsNone(f.formatted_contents)
        self.assertRaises(RuntimeError, self.get_patch_segments, f)
        self.assertRaises(RuntimeError, self.get_format_segments, f)

        # Create object with only base contents
        f = File("filename", self._base_contents)
        self.assertEqual(f.base_contents, self._base_contents)
        self.assertIsNone(f.patch_contents)
        self.assertIsNone(f.formatted_contents)
        self.assertRaises(RuntimeError, self.get_patch_segments, f)
        self.assertRaises(RuntimeError, self.get_format_segments, f)

        # Create object with only patched contents
        f = File("filename", patch=self._patch_contents)
        self.assertIsNone(f.base_contents)
        self.assertEqual(f.patch_contents, self._patch_contents)
        self.assertIsNone(f.formatted_contents)
        self.assertRaises(RuntimeError, self.get_patch_segments, f)
        self.assertRaises(RuntimeError, self.get_format_segments, f)

        # Create object with base and patch contents
        f = File("filename", self._base_contents, self._patch_contents)
        self.assertEqual(f.base_contents, self._base_contents)
        self.assertEqual(f.patch_contents, self._patch_contents)
        self.assertIsNone(f.formatted_contents)
        self.assertEqual(f.patch_segments, self._patch_segments)
        self.assertRaises(RuntimeError, self.get_format_segments, f)

    def test_content_reset(self):
        """Validate that a File object can be set/reset various times, and that triggers a recalculation of segments"""
        f = File("filename", self._base_contents, self._patch_contents)
        self.assertEqual(f.base_contents, self._base_contents)
        self.assertEqual(f.patch_contents, self._patch_contents)
        self.assertIsNone(f.formatted_contents)
        self.assertGreater(len(f.patch_segments), 0)
        self.assertRaises(RuntimeError, self.get_format_segments, f)

        # Add formatted segments
        f.formatted_contents = self._formatted_contents
        self.assertEqual(f.base_contents, self._base_contents)
        self.assertEqual(f.patch_contents, self._patch_contents)
        self.assertEqual(f.formatted_contents, self._formatted_contents)
        self.assertGreater(len(f.patch_segments), 0)
        self.assertGreater(len(f.format_segments), 0)

        # Remove patched contents (should reset all segments)
        f.patch_contents = None
        self.assertEqual(f.base_contents, self._base_contents)
        self.assertEqual(f.patch_contents, None)
        self.assertEqual(f.formatted_contents, self._formatted_contents)
        self.assertRaises(RuntimeError, self.get_patch_segments, f)
        self.assertRaises(RuntimeError, self.get_format_segments, f)

        # Validate that setting empty (patch) content is also valid. If patch contents is empty, it is a deletion only
        # so that means that there will be 0 patch segments.
        f.patch_contents = []
        self.assertEqual(f.base_contents, self._base_contents)
        self.assertEqual(f.patch_contents, [])
        self.assertEqual(f.formatted_contents, self._formatted_contents)
        self.assertEqual(len(f.patch_segments), 0)
        self.assertGreater(len(f.format_segments), 0)

        # Validate that removing formatted_contents will remove format_segments
        f.formatted_contents = None
        self.assertEqual(f.base_contents, self._base_contents)
        self.assertEqual(f.patch_contents, [])
        self.assertIsNone(f.formatted_contents)
        self.assertEqual(len(f.patch_segments), 0)
        self.assertRaises(RuntimeError, self.get_format_segments, f)

    def test_formatted_segments(self):
        """This test determines if the File class correctly determines the formatted segments"""
        f = File("filename", self._base_contents, self._patch_contents)
        f.formatted_contents = self._formatted_contents
        self.assertEqual(f.format_segments, self._format_segments)
