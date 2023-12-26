import os
import unittest

from formatchecker.runner import RevisionFile, _parse_input_diff, _run_clang_format, _parse_diff


class RunnerTest(unittest.TestCase):
    TESTCASE1_FILES = [
        ("src/apps/clock/cl_view.cpp", "49:49,52:52,54:55,60:60,62:63,67:67,69:70"),
        ("src/apps/clock/cl_wind.cpp", "25:25,37:49,51:52,61:61,83:83,85:85"),
    ]

    def setUp(self):
        # Files in testcase1.diff
        self.revisions = {}
        for f in self.TESTCASE1_FILES:
            testfile_name = "testcase1_" + os.path.basename(f[0])
            with open(os.path.join('testdata', testfile_name)) as c:
                content = c.read()
            self.revisions[f[0]] = RevisionFile(f[0], content)

    def test_patch_parser(self):
        diff = None
        with open(os.path.join('testdata', 'testcase2.diff')) as f:
            diff = f.readlines()
        segments = _parse_diff(diff)
        expected = {
            'Jamfile': [(4, 4, 3, None), (42, None, 42, 42), (64, 64, 64, 64), (84, 86, 84, 86), (92, 92, 92, 96),
                        (107, 108, 111, 111)], 'Jamrules': [(12, None, 13, 13)]}
        self.assertEqual(segments, expected)

    def test_info_diff(self):
        with open(os.path.join('testdata', 'testcase1.diff')) as diff:
            _parse_input_diff(self.revisions, diff)
        for testcase_file in self.TESTCASE1_FILES:
            segments = self.revisions[testcase_file[0]].patch_segments
            segments_strings = []
            for segment in segments:
                segments_strings.append(segment.format_range())
            self.assertEqual(testcase_file[1], ",".join(segments_strings))

    def test_run_clang_format(self):
        input_file = self.revisions[self.TESTCASE1_FILES[0][0]]
        _run_clang_format(input_file)
        self.assertIsNone(self.revisions["src/apps/clock/cl_view.cpp"].formatted_contents)
        input_file = self.revisions[self.TESTCASE1_FILES[1][0]]
        _run_clang_format(input_file)
        self.assertIsNotNone(self.revisions["src/apps/clock/cl_wind.cpp"].formatted_contents)


if __name__ == '__main__':
    unittest.main()
