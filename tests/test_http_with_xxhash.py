import json
import os

import requests

from mocket import Mocket, mocketize
from tests.test_http import HttpTestCase


class HttpEntryTestCase(HttpTestCase):
    @mocketize(truesocket_recording_dir=os.path.dirname(__file__))
    def test_truesendall_with_dump_from_recording(self):
        requests.get(
            "http://httpbin.local/ip",
            headers={
                "user-agent": "Fake-User-Agent",
                "Accept-Encoding": "gzip, deflate, zstd",
            },
        )
        requests.get(
            "http://httpbin.local/gzip",
            headers={
                "user-agent": "Fake-User-Agent",
                "Accept-Encoding": "gzip, deflate, zstd",
            },
        )

        dump_filename = os.path.join(
            Mocket.get_truesocket_recording_dir(),
            Mocket.get_namespace() + ".json",
        )
        with open(dump_filename) as f:
            responses = json.load(f)

        self.assertEqual(len(responses["httpbin.local"]["80"].keys()), 2)
