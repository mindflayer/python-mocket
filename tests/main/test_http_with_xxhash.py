# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import io
import json

import pytest
import requests

from mocket import Mocket, mocketize
from tests.main.test_http import HttpTestCase


@pytest.mark.skipif('os.getenv("SKIP_TRUE_HTTP", False)')
class TrueHttpEntryTestCase(HttpTestCase):

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
