"""Run with: PYTHONPATH=lib:. python3 -m unittest discover -s tests -v"""

import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import cherrypy
import xmltodict

import plexpy
from plexpy import helpers
from plexpy import webserve  # Register web interface methods with API2.
from plexpy.api2 import API2


class ServerNameTests(unittest.TestCase):
    def setUp(self):
        self.api_key = 'a' * 32
        config = SimpleNamespace(API_ENABLED=True, API_KEY=self.api_key)
        config_patch = patch.object(plexpy, 'CONFIG', config)
        config_patch.start()
        self.addCleanup(config_patch.stop)
        cache_patch = patch.object(API2, '_api_valid_methods_cached', None)
        cache_patch.start()
        self.addCleanup(cache_patch.stop)

    def request(self, command, **kwargs):
        return API2()._api_run(
            cmd=command, apikey=self.api_key, **kwargs)

    def register_handler(self, function, *aliases, **kwargs):
        for name in aliases or (function.__name__,):
            method_patch = patch.object(API2, name, create=True)
            method_patch.start()
            self.addCleanup(method_patch.stop)
        wrapper = helpers.addtoapi(*aliases, **kwargs)(function)
        API2._api_valid_methods_cached = None
        return wrapper

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

    def test_literal_response_option_applies_to_all_aliases(self):
        def literal_response(self, value):
            """Return a literal value."""
            return value

        aliases = ('literal_response_one', 'literal_response_two')
        wrapper = self.register_handler(
            literal_response, *aliases, parse_response=False)
        for alias in aliases:
            with self.subTest(alias=alias):
                response = json.loads(self.request(
                    alias, value='1260'))['response']
                self.assertEqual(cherrypy.response.status, 200)
                self.assertEqual(response['result'], 'success')
                self.assertEqual(response['data'], '1260')
        self.assertEqual(wrapper(None, value='1260'), '1260')

    def test_default_decorator_preserves_legacy_response_parsing(self):
        def serialized_response(self, value):
            """Return a serialized value."""
            return value

        self.register_handler(serialized_response)
        responses = (
            ('1260', 1260),
            ('true', True),
            ('{"name": "1260"}', {'name': '1260'}),
            ('[1260]', [1260]),
            ('<name>1260</name>', {'name': '1260'}),
            ({'name': '1260'}, {'name': '1260'}),
        )
        for raw, expected in responses:
            with self.subTest(raw=raw):
                response = json.loads(self.request(
                    'serialized_response', value=raw))['response']
                self.assertEqual(response['result'], 'success')
                self.assertEqual(response['data'], expected)


if __name__ == '__main__':
    unittest.main()
