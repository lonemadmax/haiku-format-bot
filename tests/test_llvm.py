#
# Copyright 2023 Haiku, Inc. All rights reserved.
# Distributed under the terms of the MIT License.
#
# Authors:
#  Niels Sascha Reedijk, niels.reedijk@gmail.com
#

import os
import unittest

from formatchecker.llvm import run_clang_format, parse_diff_segments


class LLVMTest(unittest.TestCase):
    """Test the public functions in the formatchecker.llvm module."""
    _clang_format_files = [
        # ("filename", "ranges", expect if input and output are the same)
        ("test_llvm_noreformat.cpp", ["49:49", "52:52", "54:55", "60:60", "62:63", "67:67", "69:70"], True),
        ("test_llvm_reformat.cpp", ["25:25", "37:49", "51:52", "61:61", "83:83", "85:85"], False),
    ]

    def test_run_clang_format(self):
        """This test runs clang-format over two files.
        Note that this test is likely to be sensitive to changes to the underlying clang-format version, so if it
        breaks, check first if it is due to changes in the way the formatter works.

        The current test is written for haiku-format 17.0.6."""
        data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
        for test_file in self._clang_format_files:
            with open(os.path.join(data_path, test_file[0])) as f:
                data = f.readlines()
                formatted_contents = run_clang_format(data, test_file[1])
                if test_file[2]:
                    self.assertEqual(data, formatted_contents)
                else:
                    self.assertNotEqual(data, formatted_contents)

    def test_patch_parser(self):
        """Test the diff parsing skills of the `llvm.parse_diff_segments()` function"""
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "test_llvm_patch_parser.diff")) as f:
            segments = parse_diff_segments(f)

        expected = {
            'Jamfile': [(4, 4, 3, None), (42, None, 42, 42), (64, 64, 64, 64), (84, 86, 84, 86), (92, 92, 92, 96),
                        (107, 108, 111, 111)], 'Jamrules': [(12, None, 13, 13)]}
        self.assertEqual(segments, expected)


if __name__ == '__main__':
    unittest.main()
