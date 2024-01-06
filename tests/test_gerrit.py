#
# Copyright 2023-2024 Haiku, Inc. All rights reserved.
# Distributed under the terms of the MIT License.
#
# Authors:
#  Niels Sascha Reedijk, niels.reedijk@gmail.com
#
import json
import os
import unittest

from formatchecker.gerrit import Context


def context_get_mock(self, url: str, params=None):
    data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    # ContextTest.setUpClass()
    if url == "changes/" and params is None:
        # This is the get operation to check if the Gerrit URL is valid
        return
    # ContextTest.test_get_change_id_from_number()
    elif url == "changes/" and "change:5692" in params.values():
        with open(os.path.join(data_path, "test_gerrit_get_change.json")) as f:
            return json.load(f)
    elif url == "changes/" and "change:19000" in params.values():
        return []
    # ContextTest.test_get_change()
    elif url == "changes/test_get_change/revisions/current/files":
        with open(os.path.join(data_path, "test_gerrit_revision_files.json")) as f:
            return json.load(f)
    elif url =="changes/test_get_change/revisions/current/files/%2FCOMMIT_MSG/content":
        # This file is added, so only support getting the new contents
        if params is None:
            return "COMMIT_MSG line 1\nCOMMIT_MSG line 2\n"
        elif params == {"parent": "1"}:
            raise RuntimeError("The COMMIT_MSG file is added, so the base version should not be requested")
        else:
            raise RuntimeError("Invalid request for COMMIT_MSG content")
    elif url =="changes/test_get_change/revisions/current/files/src%2Ffile_implicitly_modified/content":
        # This file is modified, so there is new and parent contents
        if params is None:
            return "file_implicitly_modified line 1\n2Ffile_implicitly_modified base line 2\n"
        elif params == {"parent": "1"}:
            return "file_implicitly_modified line 1\n2Ffile_implicitly_modified patched line 2\n"
        else:
            raise RuntimeError("Invalid request for src/file_implicitly_modified content")
    elif url =="changes/test_get_change/revisions/current/files/src%2Ffile_deleted/content":
        # This file is modified, so there is new and parent contents
        if params is None:
            raise RuntimeError("The src/file_deleted file is deleted, so the patched version should not be requested")
        elif params == {"parent": "1"}:
            return "file_deleted line 1\nfile_deleted line 2\n"
        else:
            raise RuntimeError("Invalid request for src/file_implicitly_modified content")
    raise ValueError("Input URL is not mocked: %s" % url)


class ContextTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Context._get = context_get_mock
        cls._context = Context("https://test-gerrit/")

    def test_get_change_id_from_number(self):
        self.assertEqual(self._context.get_change_and_revision_from_number(5692),
                         ("haiku~dev%2Fnetservices~I0dadd1dfd3fb36256bd6f4a2530dbbe12afefce5", "701299b"))
        self.assertRaises(ValueError, self._context.get_change_and_revision_from_number, 19000)

    def test_get_change(self):
        change = self._context.get_change("test_get_change")
        # Validate that the file content was requested correctly
        self.assertEqual(change.files[0].filename, "/COMMIT_MSG")
        self.assertIsNone(change.files[0].base_contents)
        self.assertIsNotNone(change.files[0].patch_contents)
        self.assertEqual(change.files[1].filename, "src/file_implicitly_modified")
        self.assertIsNotNone(change.files[1].base_contents)
        self.assertIsNotNone(change.files[1].patch_contents)
        self.assertEqual(change.files[2].filename, "src/file_deleted")
        self.assertIsNotNone(change.files[2].base_contents)
        self.assertIsNone(change.files[2].patch_contents)


if __name__ == '__main__':
    unittest.main()
