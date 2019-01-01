# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import io
import json
import os

import requests
from tests.main.test_http import HttpTestCase

from mocket import Mocket, mocketize


class HttpEntryTestCase(HttpTestCase):

    @mocketize(truesocket_recording_dir=os.path.dirname(__file__))
    def test_truesendall_with_dump_from_recording(self):
        requests.get('http://httpbin.org/ip', headers={"user-agent": "Fake-User-Agent"})
        requests.get('http://httpbin.org/gzip', headers={"user-agent": "Fake-User-Agent"})

        dump_filename = os.path.join(
            Mocket.get_truesocket_recording_dir(),
            Mocket.get_namespace() + '.json',
        )
        with io.open(dump_filename) as f:
            responses = json.load(f)

        self.assertEqual(len(responses['httpbin.org']['80'].keys()), 2)
