import importlib.util
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('lumen_admission', Path(__file__).resolve().parents[1] / 'scripts/lumen_checkout_admission.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class LumenCheckoutAdmissionTests(unittest.TestCase):
    def test_ignored_compiler_inputs_are_rejected(self):
        with patch.object(subprocess, 'check_output', side_effect=['a' * 40 + '\n', '', 'Sources/LumenUI/extra.swift\n']):
            with self.assertRaisesRegex(ValueError, 'Ignored Lumen'):
                module.check_checkout('/fixture', 'a' * 40)

    def test_clean_exact_checkout_is_accepted(self):
        with patch.object(subprocess, 'check_output', side_effect=['a' * 40 + '\n', '', '']):
            module.check_checkout('/fixture', 'a' * 40)

    def test_changed_checkout_is_rejected(self):
        with patch.object(subprocess, 'check_output', side_effect=['b' * 40 + '\n']):
            with self.assertRaisesRegex(ValueError, 'differs'):
                module.check_checkout('/fixture', 'a' * 40)
