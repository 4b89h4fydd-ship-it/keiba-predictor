"""CLI writes a reproducible report without touching live races or D1."""
import json
import tempfile
from pathlib import Path
from unittest import TestCase

from scripts.arvexq_frozen_research_ticket_evaluation import main


class FrozenResearchCliTests(TestCase):
    def test_empty_input_report_is_explicitly_unmeasured(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'input.json'
            output = Path(tmp) / 'report.json'
            source.write_text('[]', encoding='utf-8')
            main(['--input', str(source), '--output', str(output)])
            report = json.loads(output.read_text(encoding='utf-8'))
            self.assertEqual(report['inputRecordCount'], 0)
            self.assertIsNone(report['byCircuit']['中央']['単勝']['measuredHitRate'])
            self.assertIsNone(report['byCircuit']['地方']['3連単']['flatStakeReturnRate'])
            self.assertFalse(report['target80Achieved'])
            self.assertIn('assertions', report['provenanceCaveat'])
