"""Escaped-value budget controls on new synthetic presentation inputs."""
import json.encoder
import unittest
from unittest.mock import patch

from airs.coverage_text import render_coverage_text
from airs.types import InputError
from test_coverage_text import inventory


class CoverageTextPreflightTests(unittest.TestCase):
    def test_expansion_is_refused_before_encoding_a_large_saved_value(self):
        original = json.encoder.encode_basestring_ascii
        oversized = '\x00' * 5000
        value = inventory()
        value['reports'][0]['image'] = {'display_name': oversized}

        def bounded_encode(text):
            if text == oversized:
                self.fail('Oversized saved value reached JSON string allocation')
            return original(text)

        with patch('json.encoder.encode_basestring_ascii', side_effect=bounded_encode):
            with self.assertRaises(InputError) as caught:
                render_coverage_text(value, maximum_bytes=4096)
        self.assertEqual(caught.exception.code, 'generated_report_size_limit')
        self.assertIn('coverage text', str(caught.exception))

    def test_nested_keys_and_unicode_expansion_obey_exact_output_boundary(self):
        from copy import deepcopy
        value = inventory()
        value['reports'][0]['image'] = {'\x7f\U0001f600': ['\x00\u202e', 'é', '\ud800']}
        before = deepcopy(value)
        text = render_coverage_text(value)
        self.assertTrue(text.isascii())
        self.assertIn('"\\u007f\\ud83d\\ude00": ["\\u0000\\u202e", "\\u00e9", "\\ud800"]', text)
        self.assertEqual(render_coverage_text(value, maximum_bytes=len(text)), text)
        with self.assertRaises(InputError) as caught:
            render_coverage_text(value, maximum_bytes=len(text) - 1)
        self.assertEqual(caught.exception.code, 'generated_report_size_limit')
        self.assertEqual(value, before)

    def test_oversized_dictionary_key_is_refused_before_encoding(self):
        original = json.encoder.encode_basestring_ascii
        key = '\U0001f600' * 500
        value = inventory()
        value['models'] = {key: 2}

        def bounded_encode(text):
            if text == key:
                self.fail('Oversized saved key reached JSON string allocation')
            return original(text)

        with patch('json.encoder.encode_basestring_ascii', side_effect=bounded_encode):
            with self.assertRaises(InputError):
                render_coverage_text(value, maximum_bytes=2048)
