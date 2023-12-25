import os
import unittest

from formatchecker.runner import RevisionFile, _parse_input_diff, _run_clang_format


class RunnerTest(unittest.TestCase):
    TESTCASE1_FILES = [
        ("src/apps/clock/cl_view.cpp", "46:73"),
        ("src/apps/clock/cl_wind.cpp", "22:28,34:55,58:64,80:88"),
    ]

    def setUp(self):
        # Files in testcase1.diff
        self.revisions = {}
        for f in self.TESTCASE1_FILES:
            testfile_name = "testcase1_" + os.path.basename(f[0])
            with open(os.path.join('testdata', testfile_name)) as c:
                content = c.read()
            self.revisions[f[0]] = RevisionFile(f[0], content)

    def test_info_diff(self):
        with open(os.path.join('testdata', 'testcase1.diff')) as diff:
            _parse_input_diff(self.revisions, diff)
        for testcase_file in self.TESTCASE1_FILES:
            segments = self.revisions[testcase_file[0]].segments
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
