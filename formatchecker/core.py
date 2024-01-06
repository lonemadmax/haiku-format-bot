#
# Copyright 2023-2024 Haiku, Inc. All rights reserved.
# Distributed under the terms of the MIT License.
#
# Authors:
#  Niels Sascha Reedijk, niels.reedijk@gmail.com
#
"""
This module contains the core high-level objects and functions that are used to fetch a change,
reformat it, and publish those changes back to Gerrit.
"""
import json
import logging
import re
import sys

from .gerrit import Context
from .models import Change, ReviewInput, CommentRange, CommentInput, ReformatType, strip_empty_values_from_input_dict
from .llvm import run_clang_format

EXTENSION_PATTERN = (r"^.*\.(?:cpp|cc|c\+\+|cxx|cppm|ccm|cxxm|c\+\+m|c|cl|h|hh|hpp"
                     r"|hxx|m|mm|inc|js|ts|proto|protodevel|java|cs|json|s?vh?)$")


def reformat_change(gerrit_url:str, change_id: int | str, revision_id: str = "current", submit: bool = False):
    """Function to fetch a change, reformat it.
    The function returns a dict that contains the data that can be posted to the review endpoint on Gerrit.
    """
    logger = logging.getLogger("core")
    logger.info("Fetching change details for %s" % str(change_id))
    ctx = Context(gerrit_url)
    if isinstance(change_id, int):
        # convert a change number to an id
        change_id, revision_id = ctx.get_change_and_revision_from_number(change_id)
    change = ctx.get_change(change_id, revision_id)
    for f in change.files:
        if not re.match(EXTENSION_PATTERN, f.filename, re.IGNORECASE):
            logger.info("Ignoring %s because it does not seem to be a file that `clang-format` can handle" % f.filename)
            continue
        if f.patch_contents is None:
            logger.info("Skipping %s because the file is deleted in the patch" % f.filename)
            continue
        if len(f.patch_segments) == 0:
            logger.info("Skipping %s because the changes in the patch are only deletions" % f.filename)
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

    review_input = _change_to_review_input(change)
    # Convert review input into json
    if submit:
        ctx.publish_review(change_id, review_input, revision_id)
        logger.info("The review has been submitted to Gerrit")
    else:
        output = strip_empty_values_from_input_dict(review_input)
        with open("review.json", "wt") as f:
            f.write(json.dumps(output, indent=4))
        url = "%sa/changes/%s/revisions/%s/review" % (gerrit_url, change_id, revision_id)
        logger.info("POST the contents of review.json to: %s", url)


def _change_to_review_input(change: Change) -> ReviewInput:
    """Internal function that converts a change into a ReviewInput object that can be pushed to Gerrit"""
    comments: dict[str, list[CommentInput]] = {}
    for f in change.files:
        if f.formatted_contents is None or len(f.format_segments) == 0:
            continue
        for segment in f.format_segments:
            end = segment.end
            match segment.reformat_type:
                case ReformatType.INSERTION:
                    end = segment.start
                    operation = "insert after"
                case ReformatType.MODIFICATION:
                    operation = "change"
            # As per the documentation, set the end point to character 0 of the next line to select all lines
            # between start_line and end_line (excluding any content of end_line)
            # https://review.haiku-os.org/Documentation/rest-api-changes.html#comment-range
            # However, this does not seem to work with Gerrit 3.7.1 as it seems to select the entirety of end_line
            # as well. So comment this out, put keeping a note just in case this is a bug in this particular Gerrit
            # version and it needs to come back in the future.
            # end += 1
            comment_range = CommentRange(segment.start, 0, end, 0)
            if segment.reformat_type == ReformatType.DELETION:
                message = "Suggestion from `haiku-format` is to remove this line/these lines."
            else:
                message = ("Suggestion from `haiku-format` (%s):\n```c++\n%s```"
                           % (operation, "".join(segment.formatted_content)))
            comments.setdefault(f.filename, []).extend([CommentInput(
                message=message, range=comment_range
            )])

    if len(comments) == 0:
        message = "Experimental `haiku-format` bot: no formatting changes suggested for this commit."
    else:
        message = ("Experimental `haiku-format` bot: some formatting changes suggested.\nNote that this bot is "
                   "experimental and the suggestions may not be correct. There is a known issue with changes "
                   "in header files: `haiku-format` does not yet correctly output the column layout of the contents "
                   "of classes.\n\nYou can see and apply the suggestions by running `haiku-format` in your local "
                   "repository. For example, if in your local checkout this change is applied to a local checkout, you "
                   "can use the following command to automatically reformat:\n```\ngit-haiku-format HEAD~\n```")

    return ReviewInput(message=message, comments=comments)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        prog="format-check",
        description="Checks the formatting of a patch on Haiku's Gerrit instance and publishes reformats if necessary")
    parser.add_argument('--submit', action="store_true", help="submit the review to gerrit")
    parser.add_argument('change_number', type=int)
    args = parser.parse_args()
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    reformat_change("https://review.haiku-os.org/", args.change_number, submit=args.submit)
