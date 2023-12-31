#
# Copyright 2023 Haiku, Inc. All rights reserved.
# Distributed under the terms of the MIT License.
#
# Authors:
#  Niels Sascha Reedijk, niels.reedijk@gmail.com
#

import os
import unittest

from formatchecker.models import File, ReformatType
from formatchecker.llvm import run_clang_format, parse_diff_segments


class RunnerTest(unittest.TestCase):
    TESTCASE1_FILES = [
        # ("filename", "ranges", expect formatting changes)
        ("src/apps/clock/cl_view.cpp", "49:49,52:52,54:55,60:60,62:63,67:67,69:70", False),
        ("src/apps/clock/cl_wind.cpp", "25:25,37:49,51:52,61:61,83:83,85:85", True),
    ]

    def test_runner_flow(self):
        # Set up files in testcase1.diff
        self.revisions = {}
        for f in self.TESTCASE1_FILES:
            testfile_name = "testcase1_base_" + os.path.basename(f[0])
            with open(os.path.join('testdata', testfile_name)) as c:
                base = c.readlines()
            testfile_name = "testcase1_patched_" + os.path.basename(f[0])
            with open(os.path.join('testdata', testfile_name)) as c:
                patch = c.readlines()
            self.revisions[f[0]] = File(f[0], base, patch)

        # Test if the patch segments have been identified correctly (File._calculate_patch_segments)
        for testcase_file in self.TESTCASE1_FILES:
            segments = self.revisions[testcase_file[0]].patch_segments
            segments_strings = []
            for segment in segments:
                segments_strings.append(segment.format_range())
            self.assertEqual(testcase_file[1], ",".join(segments_strings))

        # Test runner.run_clang_format
        for testcase_file in self.TESTCASE1_FILES:
            segments = []
            for segment in self.revisions[testcase_file[0]].patch_segments:
                segments.append("%i:%i" % (segment.start, segment.end))
            formatted_contents = run_clang_format(self.revisions[testcase_file[0]].patch_contents, segments)
            self.revisions[testcase_file[0]].formatted_contents = formatted_contents
            if testcase_file[2]:
                # we are expecting a value
                self.assertIsNotNone(self.revisions[testcase_file[0]].formatted_contents)
            else:
                self.assertIsNone(self.revisions[testcase_file[0]].formatted_contents)

        # Test if the File object correctly calculates the reformatted segments
        input_file = self.revisions[self.TESTCASE1_FILES[1][0]]
        self.assertEqual(len(input_file.format_segments), 3)
        self.assertEqual(input_file.format_segments[0].reformat_type, ReformatType.MODIFICATION)
        self.assertTrue(input_file.format_segments[0].start, 25)
        self.assertTrue(input_file.format_segments[0].end, 25)
        self.assertEqual(len(input_file.format_segments[0].formatted_content), 1)
        self.assertEqual(input_file.format_segments[1].reformat_type, ReformatType.MODIFICATION)
        self.assertTrue(input_file.format_segments[1].start, 37)
        self.assertTrue(input_file.format_segments[1].end, 49)
        self.assertEqual(len(input_file.format_segments[1].formatted_content), 12)
        self.assertEqual(input_file.format_segments[2].reformat_type, ReformatType.MODIFICATION)
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
