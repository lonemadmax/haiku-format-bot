#
# Copyright 2023 Haiku, Inc. All rights reserved.
# Distributed under the terms of the MIT License.
#
# Authors:
#  Niels Sascha Reedijk, niels.reedijk@gmail.com
#
"""
This module contains the core high-level objects and functions that are used to fetch a change,
reformat it, and publish those changes back to Gerrit.
"""
import logging
import re
import sys

from .gerrit import Context
from .llvm import run_clang_format

EXTENSION_PATTERN = (r"^.*\.(?:cpp|cc|c\+\+|cxx|cppm|ccm|cxxm|c\+\+m|c|cl|h|hh|hpp"
                     r"|hxx|m|mm|inc|js|ts|proto|protodevel|java|cs|json|s?vh?)$")


def reformat_change(gerrit_url:str, change_id: int | str):
    """Function to fetch a change, reformat it, and publish the improvements to Gerrit"""
    logger = logging.getLogger("core")
    ctx = Context(gerrit_url)
    if isinstance(change_id, int):
        # convert a change number to an id
        change_id = ctx.get_change_id_from_number(change_id)
    change = ctx.get_change(change_id)
    for f in change.files:
        if not re.match(EXTENSION_PATTERN, f.filename, re.IGNORECASE):
            logger.info("Ignoring %s because it does not seem to be a file that `clang-format` can handle" % f.filename)
            continue
        if f.patch_contents is None:
            logger.info("Skipping %s because the file is deleted in the patch" % f.filename)
            continue
        segments = []
        for segment in f.patch_segments:
            segments.append(segment.format_range())
        reformatted_content = run_clang_format(f.patch_contents, segments)
        f.formatted_contents = reformatted_content
        if f.formatted_contents is None:
            logger.info("%s: no reformats" % f.filename)
        else:
            logger.info("%s: %i segment(s) reformatted" % (f.filename, len(f.format_segments)))


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        prog="format-check",
        description="Checks the formatting of a patch on Haiku's Gerrit instance and publishes reformats if necessary")
    parser.add_argument('change_number', type=int)
    args = parser.parse_args()
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    reformat_change("https://review.haiku-os.org/", args.change_number)
