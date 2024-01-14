#
# Copyright 2023-2024 Haiku, Inc. All rights reserved.
# Distributed under the terms of the MIT License.
#
# Authors:
#  Niels Sascha Reedijk, niels.reedijk@gmail.com
#
import json
import logging
import os
from functools import reduce
from io import StringIO
from typing import Any

import requests
from base64 import b64decode
from urllib.parse import quote, urljoin

from .models import Change, File, ReviewInput, strip_empty_values_from_input_dict


class Context:
    """Class for sending/receiving with a Gerrit instance"""

    def __init__(self, url: str):
        """Set the Gerrit instance to a URL. A basic test is performed to make sure it is valid."""
        self._gerrit_url = url
        self._gerrit_auth = None
        self._logger = logging.getLogger("gerrit")
        _ = self._get("changes/")
        self._logger.info("Context for gerrit instance: %s" % str(url))

    def get_change(self, change_id: str, revision_id: str = "current") -> Change:
        """Get a change including its details from Gerrit. Optionally it is possible to get a specific revision."""
        current_revision_url = "changes/%s/revisions/%s/" % (change_id, revision_id)
        change_dict: dict = self._get(urljoin(current_revision_url, "files"))
        files = []
        for filename in change_dict.keys():
            status = change_dict[filename].get("status", "M")
            file_get_url = urljoin(current_revision_url, "files/%s/content" % quote(filename, safe=''))
            if status not in ["M", "D", "A"]:
                raise RuntimeError("Unsupported file status change")
            # get the contents of the current patch version of the file
            if status != "D":
                patch_content = self._get(file_get_url)
                patch_content = StringIO(patch_content).readlines()
            else:
                patch_content = None
            if status != "A":
                base_content = self._get(file_get_url, params={"parent": "1"})
                base_content = StringIO(base_content).readlines()
            else:
                base_content = None
            files.append(File(filename, base_content, patch_content))
        return Change(change_id, files)

    def get_change_and_revision_from_number(self, change_number: int) -> tuple[str, str]:
        """Retrieve the change id and latest revision id from a change number"""
        changes: list[Any] = self._get("changes/",
                                       params={"q": "change:%i" % change_number, "o": "CURRENT_REVISION"})
        if len(changes) == 0:
            raise ValueError("Invalid change number")
        return changes[0]["id"], changes[0]["current_revision"]

    def publish_review(self, change_id: str, review: ReviewInput, revision_id: str = "current"):
        """Post a review to a change."""
        review_url = "changes/%s/revisions/%s/review" % (change_id, revision_id)#
        data = strip_empty_values_from_input_dict(review)
        self._post(review_url, data)

    def _get(self, url: str, params=None) -> list[Any] | dict[str, Any] | str:
        """Get resources from Gerrit and do some basic validations.
        Depending on the type of request, the return value is either a list (from JSON), a dict (from JSON) or plain
        text (which has been sent as base64 encoded value).
        """
        url = urljoin(self._gerrit_url, url)
        response = requests.get(url, params=params)
        self._logger.debug("GET %s: status: %i" % (url, response.status_code))
        if response.status_code != 200:
            raise RuntimeError("Invalid response from %s: %i (expected 200)" % (response.url, response.status_code))
        if response.headers['Content-Type'].startswith("application/json"):
            if not response.text.startswith(")]}'"):
                raise RuntimeError("Invalid response from %s: content does not start with marker" % response.url)
            return json.loads(response.text[4:])
        elif (response.headers['Content-Type'].startswith("text/plain")
              and response.headers["X-FYI-Content-Encoding"] == "base64"):
            return b64decode(response.text).decode("utf-8")
        else:
            raise RuntimeError("Invalid content type: %s" % response.headers['Content-Type'])

    def _post(self, url: str, content: list[Any] | dict[str, Any]):
        """Post content to Gerrit. The input is expected to be data that can be encoded to JSON.
        This input URL is the Gerrit URL that the API documentation proposes data is posted to. This method prepends the
        'a' path segment to the URL to make sure it is authenticated.

        The method requires GERRIT_USERNAME and GERRIT_PASSWORD environment variables to be set.
        """
        url = reduce(urljoin, [self._gerrit_url, "a/", url])
        response = requests.post(url, json=content, auth=self.auth)
        self._logger.debug("POST %s: status: %i" % (url, response.status_code))
        if response.status_code != 200:
            raise RuntimeError("Invalid response from %s: %i (expected 200)" % (response.url, response.status_code))
        if response.headers['Content-Type'].startswith("application/json"):
            if not response.text.startswith(")]}'"):
                raise RuntimeError("Invalid response from %s: content does not start with marker" % response.url)
            return json.loads(response.text[4:])
        else:
            raise RuntimeError("Invalid content type: %s" % response.headers['Content-Type'])

    @property
    def auth(self) -> tuple[str, str]:
        if self._gerrit_auth is None:
            try:
                username = os.environ["GERRIT_USERNAME"]
                password = os.environ["GERRIT_PASSWORD"]
            except KeyError:
                raise RuntimeError("In order to post contents, the GERRIT_USERNAME and GERRIT_PASSWORD environment "
                                   "variable should be set")
            self._gerrit_auth = (username, password)
        return self._gerrit_auth
