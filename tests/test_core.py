#
# Copyright 2024 Haiku, Inc. All rights reserved.
# Distributed under the terms of the MIT License.
#
# Authors:
#  Niels Sascha Reedijk, niels.reedijk@gmail.com
#
import os
import unittest

from formatchecker.core import get_class_lines_in_file

class ClassFinderTest(unittest.TestCase):
    def test_classfinder(self):
        data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
        with open(os.path.join(data_path, "test_class_finder.cpp")) as f:
            contents = f.readlines()
            self.assertEqual(get_class_lines_in_file(contents),
                             [14, 19, 20, 21, 38, 39, 40, 41, 42, 43, 44, 45, 46 ,47, 53, 54])
