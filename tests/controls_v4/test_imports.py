import subprocess
import sys
from pathlib import Path
import unittest
class ImportTests(unittest.TestCase):
    def test_analysis_helper_does_not_shadow_standard_library(self):
        folder=Path(__file__).resolve().parents[2]/'scripts/controls_v4'
        p=subprocess.run([sys.executable,'-c','from statistics import median; assert median([1,3,5]) == 3'],cwd=folder,capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr)
