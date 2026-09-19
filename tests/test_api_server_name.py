"""Run with: PYTHONPATH=lib:. python3 -m unittest discover -s tests -v"""

import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import cherrypy
import xmltodict

import plexpy
from plexpy import webserve  # Register web interface methods with API2.
from plexpy.api2 import API2


class ServerNameTests(unittest.TestCase):
    def setUp(self):
        self.api_key = 'a' * 32
        config = SimpleNamespace(API_ENABLED=True, API_KEY=self.api_key)
        config_patch = patch.object(plexpy, 'CONFIG', config)
        config_patch.start()
        self.addCleanup(config_patch.stop)
        self.api = API2()

    def request(self, command, **kwargs):
        return API2()._api_run(
            cmd=command, apikey=self.api_key, **kwargs)

    def test_server_name_remains_a_string(self):
        names = (
            '1260', '0', '-1', '1.5', '1e3', 'true', 'false', 'null',
            '"1260"', '[1260]', '{"name": "1260"}',
            '<name>1260</name>', '1260 Plex', 'Winterfell-Server',
        )
        for name in names:
            with self.subTest(name=name), patch.object(
                    webserve.pmsconnect, 'get_server_friendly_name',
                    return_value=name):
                response = json.loads(
                    self.request('get_server_friendly_name'))['response']
                self.assertEqual(cherrypy.response.status, 200)
                self.assertEqual(response['result'], 'success')
                self.assertIsInstance(response['data'], str)
                self.assertEqual(response['data'], name)

    def test_server_name_with_xml_output(self):
        with patch.object(webserve.pmsconnect, 'get_server_friendly_name',
                          return_value='1260'):
            response = xmltodict.parse(self.request(
                'get_server_friendly_name', out_type='xml'))['response']
        self.assertEqual(response['result'], 'success')
        self.assertEqual(response['data'], '1260')

    def test_server_preferences_remain_strings(self):
        for value in ('1260', '0', 'true', 'false', '[1260]'):
            with self.subTest(value=value), patch.object(
                    webserve.pmsconnect.PmsConnect, 'get_server_pref',
                    return_value=value), patch.object(
                    webserve.pmsconnect.PmsConnect, '__init__',
                    return_value=None):
                response = json.loads(self.request(
                    'get_server_pref', pref='FriendlyName'))['response']
                self.assertEqual(response['result'], 'success')
                self.assertIsInstance(response['data'], str)
                self.assertEqual(response['data'], value)

    def test_other_commands_still_decode_structured_responses(self):
        responses = (
            ('{"name": "1260"}', {'name': '1260'}),
            ('[1260]', [1260]),
            ('<name>1260</name>', {'name': '1260'}),
            ({'name': '1260'}, {'name': '1260'}),
        )
        for raw, expected in responses:
            with self.subTest(raw=raw), patch.object(
                    API2, 'get_server_info', return_value=raw):
                response = json.loads(
                    self.request('get_server_info'))['response']
                self.assertEqual(response['result'], 'success')
                self.assertEqual(response['data'], expected)


if __name__ == '__main__':
    unittest.main()
