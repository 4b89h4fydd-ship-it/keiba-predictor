"""Rerunnable paired ablations of checkpointed, fact-recovered race inputs."""
import json
import os
from pathlib import Path
from arvexq.research.contextual_role_candidate import predict
from scripts.arvexq_contextual_role_comparison import evaluate


def main():
    root=Path(os.getenv('ARVEXQ_REPLAY_OUTPUT','/tmp/arvexq-contextual-official-replay'))
    cards=[]
    for path in sorted(root.glob('*.json')):
        card=json.loads(path.read_text())
        if card.get('horses') and card.get('result'):cards.append(card)
    original=Path('/tmp/arvexq-three-complete-cards.json')
    if original.exists():cards.extend(json.loads(original.read_text()))
    all_components=('blend','win','axis','slots','special')
    variants={'all':None,'unchanged':(),**{k:(k,) for k in all_components},
        **{'without-'+k:tuple(c for c in all_components if c!=k) for k in all_components}}
    report={}
    for label,components in variants.items():
        r=evaluate(cards,predictor=lambda d:predict(d,components=components))
        report[label]=r
        for circuit,phases in r['groups'].items():
            for phase,values in phases.items():
                if values['races']:
                    print(label,circuit,phase,values['races'],values['baseline'],values['candidate'],flush=True)
    (root/'component-comparison.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print('COMPONENT_AUDIT_GATE',{name:r['status'] for name,r in report.items()},flush=True)


if __name__=='__main__':main()
