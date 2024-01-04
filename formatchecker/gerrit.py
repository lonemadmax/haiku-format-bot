#
# Copyright 2023-2024 Haiku, Inc. All rights reserved.
# Distributed under the terms of the MIT License.
#
# Authors:
#  Niels Sascha Reedijk, niels.reedijk@gmail.com
#
import json
import logging
from io import StringIO
from typing import Any

import requests
from base64 import b64decode
from urllib.parse import quote, urljoin

from .models import Change, File


class Context:
    """Class for sending/receiving with a Gerrit instance"""
    def __init__(self, url: str):
        """Set the Gerrit instance to a URL. A basic test is performed to make sure it is valid."""
        self._gerrit_url = url
        self._logger = logging.getLogger("gerrit")
        response = self._get("changes/", params=None)
        self._logger.info("Context for gerrit instance: %s" % str(url))

    def get_change(self, change_id: str) -> Change:
        """Get a change including its details from Gerrit"""
        current_revision_url = urljoin(self._gerrit_url, "changes/%s/revisions/current/" % change_id)
        response = requests.get(urljoin(current_revision_url, "files"))
        if response.status_code != 200:
            raise RuntimeError("Invalid response from %s: %i (expected 200)" % (response.url, response.status_code))
        change_dict: dict = json.loads(response.text[4:])
        files = []
        for filename in change_dict.keys():
            status = change_dict[filename].get("status", "M")
            file_get_url = urljoin(current_revision_url, "files/%s/content" % quote(filename, safe=''))
            # get the contents of the current patch version of the file
            if status != "D":
                response = requests.get(file_get_url)
                if response.status_code != 200:
                    raise RuntimeError("Invalid response from %s: %i (expected 200)" % (response.url, response.status_code))
                patch_content = b64decode(response.text).decode("utf-8")
            else:
                patch_content = ""
            if status != "A":
                response = requests.get(file_get_url, params={"parent": "1"})
                if response.status_code != 200:
                    raise RuntimeError("Invalid response from %s: %i (expected 200)" % (response.url, response.status_code))
                base_content = b64decode(response.text).decode("utf-8")
            else:
                base_content = ""
            files.append(File(filename, StringIO(base_content).readlines(), StringIO(patch_content).readlines()))
        return Change(change_id, files)

    def get_change_id_from_number(self, change_number: int):
        """Convert a change number (common in the URL) into a change id"""
        changes = self._get("changes/", params={"q": "change:%i" % change_number})
        if len(changes) == 0:
            raise ValueError("Invalid change number")
        return changes[0]["id"]

    def _get(self, url: str, params) -> list[Any] | dict[str, Any]:
        url = urljoin(self._gerrit_url, url)
        response = requests.get(url, params=params)
        self._logger.debug("Request to %s: status: %i" % (url, response.status_code))
        if response.status_code != 200:
            raise RuntimeError("Invalid response from %s: %i (expected 200)" % (response.url, response.status_code))
        if not response.text.startswith(")]}'"):
            raise RuntimeError("Invalid response from %s: content does not start with marker" % response.url)
        return json.loads(response.text[4:])
