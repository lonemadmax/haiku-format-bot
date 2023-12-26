#
# Copyright 2023 Haiku, Inc. All rights reserved.
# Distributed under the terms of the MIT License.
#
# Authors:
#  Niels Sascha Reedijk, niels.reedijk@gmail.com
#
"""
This module contains the model classes that are shared between the various modules of this tool.
"""
class File:
    """Represents a file in Gerrit, including its content"""
    def __init__(self, filename: str, base: list[str] | None, patch: list[str] | None):
        self.filename = filename
        self.base = base
        self.patch = patch

    def __repr__(self):
        return "Gerrit file %s" % self.filename


class Change:
    """Represents a change in Gerrit, including a list of files"""
    def __init__(self, change_id: str, files: list[File]):
        self.change_id = change_id
        self.files = files

    def __repr__(self):
        return "Gerrit change %s" % self.change_id
