"""Retain healthy fields on partial updates and immutable pre-off artifacts."""
import copy
import json
from arvexq.prediction.prerace_archive import sealed_lock

# Transient readiness/audit metadata belongs to the current refresh attempt.
_TRANSIENT = {'preparedMeta', 'dataCoreHealth', 'predictionAudit'}
_POSITIVE = {'distance', 'fieldSize', 'raceNumber', 'horseNumber', 'frameNumber',
             'age', 'bodyWeight', 'carriedWeight', 'winOdds', 'popularity'}


def _missing(key, value):
    return value is None or value == '' or value == [] or value == {} \
        or (key in {'weather', 'condition'} and value == '不明') \
        or (key in _POSITIVE and value == 0)


def _runs(previous, incoming):
    """Union full career only; display recentRaces remains the incoming list."""
    def key(run):
        return json.dumps([run.get(k) for k in ('raceId','date','track','raceNumber','title','distance','finish','timeSeconds')],
                          ensure_ascii=False, default=str)
    by_key={key(run):run for run in previous if isinstance(run,dict)}
    out=[];seen=set()
    for run in incoming:
        if not isinstance(run,dict):
            out.append(copy.deepcopy(run));continue
        identity=key(run);seen.add(identity)
        out.append(_merge(by_key.get(identity,{}),run))
    out.extend(copy.deepcopy(run) for run in previous if isinstance(run,dict) and key(run) not in seen)
    return out


def _merge(previous, incoming):
    out=copy.deepcopy(incoming)
    for key, old in previous.items():
        if key in _TRANSIENT:
            continue
        new=out.get(key)
        if key not in out or _missing(key,new):
            out[key]=copy.deepcopy(old)
        elif isinstance(old,dict) and isinstance(new,dict):
            out[key]=_merge(old,new)
        elif key=='horses' and isinstance(old,list) and isinstance(new,list):
            by_no={h.get('horseNumber'):h for h in old if isinstance(h,dict)}
            # A nonempty official card controls starters; never re-add a withdrawn horse.
            out[key]=[_merge(by_no.get(h.get('horseNumber'),{}),h) if isinstance(h,dict) else h for h in new]
        elif key=='allPastRuns' and isinstance(old,list) and isinstance(new,list):
            out[key]=_runs(old,new)
    return out


def retain_snapshot(previous, incoming):
    if not isinstance(previous,dict) or not isinstance(incoming,dict):
        return incoming
    if previous.get('id') != incoming.get('id'):
        return incoming
    out=_merge(previous,incoming)
    if sealed_lock(previous):
        for key in ('preRacePrediction','preRaceBet','researchShadow','researchFactorShadow',
                    'morningPicks','morningMarkSnapshot','morningSelectionSnapshot'):
            if key in previous:
                out[key]=copy.deepcopy(previous[key])
        meta=dict(out.get('preparedMeta') or {})
        for key in ('preRaceSealEpoch','preRaceSealRevision','preRaceSealVersion'):
            if key in (previous.get('preparedMeta') or {}):
                meta[key]=previous['preparedMeta'][key]
        if meta:out['preparedMeta']=meta
    # A recorded pre-off ticket and morning history cannot be replaced by a refresh.
    for key in ('preRaceBet','morningPicks','morningMarkSnapshot','morningSelectionSnapshot'):
        if isinstance(previous.get(key),(dict,list)) and previous[key]:
            out[key]=copy.deepcopy(previous[key])
    return out
