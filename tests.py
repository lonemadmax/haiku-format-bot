#
# Copyright 2023 Haiku, Inc. All rights reserved.
# Distributed under the terms of the MIT License.
#
# Authors:
#  Niels Sascha Reedijk, niels.reedijk@gmail.com
#

import os
import unittest

from formatchecker.models import File
from formatchecker.llvm import _parse_input_diff, _run_clang_format, parse_diff_segments, \
    _split_format_segments


class RunnerTest(unittest.TestCase):
    TESTCASE1_FILES = [
        ("src/apps/clock/cl_view.cpp", "49:49,52:52,54:55,60:60,62:63,67:67,69:70"),
        ("src/apps/clock/cl_wind.cpp", "25:25,37:49,51:52,61:61,83:83,85:85"),
    ]

    def test_runner_flow(self):
        # Set up files in testcase1.diff
        self.revisions = {}
        for f in self.TESTCASE1_FILES:
            testfile_name = "testcase1_" + os.path.basename(f[0])
            with open(os.path.join('testdata', testfile_name)) as c:
                content = c.readlines()
            self.revisions[f[0]] = File(f[0], content, content)
        print("setup")

        # Test runner._parse_info_diff
        with open(os.path.join('testdata', 'testcase1.diff')) as diff:
            _parse_input_diff(self.revisions, diff)
        for testcase_file in self.TESTCASE1_FILES:
            segments = self.revisions[testcase_file[0]].patch_segments
            segments_strings = []
            for segment in segments:
                segments_strings.append(segment.format_range())
            self.assertEqual(testcase_file[1], ",".join(segments_strings))

        # Test runner._run_clang_format
        input_file = self.revisions[self.TESTCASE1_FILES[0][0]]
        _run_clang_format(input_file)
        self.assertIsNone(self.revisions["src/apps/clock/cl_view.cpp"].formatted_contents)
        input_file = self.revisions[self.TESTCASE1_FILES[1][0]]
        _run_clang_format(input_file)
        self.assertIsNotNone(self.revisions["src/apps/clock/cl_wind.cpp"].formatted_contents)

        # Test parser._split_format_segments
        input_file = self.revisions[self.TESTCASE1_FILES[1][0]]
        self.assertIsNotNone(self.revisions["src/apps/clock/cl_wind.cpp"].formatted_contents)
        _split_format_segments(input_file)
        self.assertEqual(len(input_file.format_segments), 3)
        self.assertTrue(input_file.format_segments[0].is_modification())
        self.assertTrue(input_file.format_segments[0].start, 25)
        self.assertTrue(input_file.format_segments[0].end, 25)
        self.assertEqual(len(input_file.format_segments[0].formatted_content), 1)
        self.assertTrue(input_file.format_segments[1].is_modification())
        self.assertTrue(input_file.format_segments[1].start, 37)
        self.assertTrue(input_file.format_segments[1].end, 49)
        self.assertEqual(len(input_file.format_segments[1].formatted_content), 12)
        self.assertTrue(input_file.format_segments[2].is_modification())
        self.assertTrue(input_file.format_segments[2].start, 51)
        self.assertTrue(input_file.format_segments[2].end, 52)
        self.assertEqual(len(input_file.format_segments[2].formatted_content), 3)

    def test_patch_parser(self):
        with open(os.path.join('testdata', 'testcase2.diff')) as f:
            segments = parse_diff_segments(f)

        expected = {
            'Jamfile': [(4, 4, 3, None), (42, None, 42, 42), (64, 64, 64, 64), (84, 86, 84, 86), (92, 92, 92, 96),
                        (107, 108, 111, 111)], 'Jamrules': [(12, None, 13, 13)]}
        self.assertEqual(segments, expected)


if __name__ == '__main__':
    unittest.main()
