# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import io
import json
import os

import requests

from mocket import Mocket, mocketize
from tests.main.test_http import HttpTestCase


class HttpEntryTestCase(HttpTestCase):
    @mocketize(truesocket_recording_dir=os.path.dirname(__file__))
    def test_truesendall_with_dump_from_recording(self):
        requests.get(
            "http://httpbin.local/ip", headers={"user-agent": "Fake-User-Agent"}
        )
        requests.get(
            "http://httpbin.local/gzip", headers={"user-agent": "Fake-User-Agent"}
        )

        dump_filename = os.path.join(
            Mocket.get_truesocket_recording_dir(),
            Mocket.get_namespace() + ".json",
        )
        with io.open(dump_filename) as f:
            responses = json.load(f)

        self.assertEqual(len(responses["httpbin.local"]["80"].keys()), 2)
