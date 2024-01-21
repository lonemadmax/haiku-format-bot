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

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        prog="haiku-format-bot",
        description="Automates running `haiku-format` on changes on Haiku's Gerrit instance")
    args = parser.parse_args()
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
