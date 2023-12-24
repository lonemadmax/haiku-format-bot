import os
import unittest

from formatchecker.runner import RevisionFile, _parse_input_diff


class RunnerTest(unittest.TestCase):
    TESTCASE1_FILES = [
        ("headers/os/drivers/ACPI.h", "253:259"),
        ("src/add-ons/kernel/bus_managers/acpi/ACPIPrivate.h", "116:122,219:225"),
        ("src/add-ons/kernel/bus_managers/acpi/BusManager.cpp", "525:531,552:562"),
        ("src/add-ons/kernel/bus_managers/acpi/Module.cpp", "101:112,125:145,154:160"),
        ("src/add-ons/kernel/bus_managers/acpi/NamespaceDump.cpp", "114:120"),
        ("src/add-ons/kernel/busses/i2c/pch/pch_i2c.cpp", "338:344")
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


if __name__ == '__main__':
    unittest.main()
