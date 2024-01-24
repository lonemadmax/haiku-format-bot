#
# Copyright 2024 Haiku, Inc. All rights reserved.
# Distributed under the terms of the MIT License.
#
# Authors:
#  Niels Sascha Reedijk, niels.reedijk@gmail.com
#
"""
This module implements the logic to select changes for Gerrit that need to be formatted, apply the formatting, and
submit the reviews. It includes error handling, in order to let the system skip changes that cannot be reformatted due
to a bug in this bot, or at any other layer.

The module can run independently.
"""
import logging
import sys
from datetime import date, timedelta

from .gerrit import Context


_ALL_CHANGES_QUERY_OPTIONS = list([
    "status:open",
    "repo:haiku",
    "-is:wip",
    "-label:Haiku-Format",
    "-hashtag:format-bot-skip",
    "-hashtag:format-bot-failed",
    "limit:100"
])


def format_changes(after: date):
    """Fetch all relevant changes from Gerrit, and apply haiku-format.

    This method is designed to be called repeatedly.
    """
    logger = logging.getLogger("runner")
    logger.info("Fetching all changes from Gerrit")
    context = Context("https://review.haiku-os.org/")
    query_options = _ALL_CHANGES_QUERY_OPTIONS.copy()
    query_options.append("after:%i-%i-%i" % (after.year, after.month, after.day))
    changes = context.query_changes(query_options, {"o": "CURRENT_REVISION"})
    logger.info("Found %i changes" % len(changes))


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        prog="haiku-format-bot",
        description="Automates running `haiku-format` on changes on Haiku's Gerrit instance")
    parser.add_argument("--days", type=int, default=3,
                        help="Number of days in the past to select changes for reformatting")
    args = parser.parse_args()
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    start_date = date.today() - timedelta(days = args.days)
    format_changes(start_date)
