#!/usr/bin/env python3
"""Offline frozen research ticket evaluation (no production writes).

Input is a JSON list of race records with independently audited pre-off
provenance. Boolean verification flags are supplied evidence assertions,
not independently verified by this script. Human/source audit is mandatory.
"""
import argparse
import json
from pathlib import Path
from arvexq.backtest.frozen_research_tickets import evaluate_frozen_candidates


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    source = json.loads(args.input.read_text(encoding='utf-8'))
    if not isinstance(source, list):
        parser.error('input must be a list of frozen race records')
    report = evaluate_frozen_candidates(source)
    report['inputRecordCount'] = len(source)
    report['provenanceCaveat'] = (
        'Source verification flags are assertions. Independently verify the '
        'timestamp, immutable snapshot hashes, collection time and training split '
        'before reporting historical accuracy.'
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'records': len(source), 'excluded': report['excluded'],
                      'output': str(args.output)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
