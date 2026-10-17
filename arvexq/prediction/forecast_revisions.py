"""Append-only recalculations with a replaceable latest-display pointer.

Original pre-off receipts are never rewritten. Recalculations after post are
retrospective analyses and are not eligible for pre-off accuracy reporting.
"""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
from math import isfinite

from arvexq.prediction.new_forecast import build_forecast

VERSION='arvexq-forecast-revision-v1'
ORIGINAL_KEYS=('preRacePrediction','preRaceBet','morningMarkSnapshot','officialMarkRevisions',
               'modelMarkRevisions','massFeatureArchive','massFeatureSnapshot','massFeatureHash')


def digest(value):
    return sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def originals_hash(detail):
    return digest({key:detail.get(key) for key in ORIGINAL_KEYS})


def input_hash(detail):
    keys=('date','track','raceNumber','circuit','surface','distance','direction','condition','class')
    horse_keys=('horseNumber','name','birthDate','jockey','trainer','carriedWeight','recentRaces','allPastRuns','careerArchive')
    return digest({'race':{k:detail.get(k) for k in keys},
                   'horses':[{k:h.get(k) for k in horse_keys} for h in detail.get('horses',[])]})


def latest_revision(detail):
    revisions=detail.get('forecastRevisions') or []
    current=detail.get('currentForecastRevisionId')
    matches=[r for r in revisions if isinstance(r,dict) and r.get('revisionId')==current
             and r.get('version')==VERSION and r.get('raceId')==detail.get('id')
             and r.get('raceDate')==detail.get('date')]
    if len(matches)!=1:
        return None
    revision=matches[0]
    expected=digest({k:v for k,v in revision.items() if k not in ('revisionId','createdAt')})
    return revision if expected==current else None


def append_revision(detail, model=None, *, at=None):
    if not detail.get('id') or not detail.get('date'):
        raise ValueError('race identity required')
    before=originals_hash(detail)
    analysis=build_forecast(detail,model)
    scenario=(analysis.get('scenarioAnalysis') or {}).get('scenarios') or []
    usual=next((s for s in scenario if s['id']=='usual'),None)
    horses=[]
    for horse in analysis.get('horses',[]):
        ev=horse.get('integratedEvaluation') or {}
        no=int(horse.get('horseNumber') or 0)
        probabilities=(usual or {}).get('probabilities',{}).get(no,{})
        if any(not isfinite(float(p)) or not -1e-9<=p<=1+1e-9 for p in probabilities.values()):
            raise ValueError('invalid revision probability')
        horses.append({'horseNumber':no,'mark':ev.get('mark',''),
            'reason':ev.get('markReason',''),'forecastText':ev.get('forecastText',''),
            'probabilities':probabilities,'probabilityRanges':ev.get('modelProbabilities',{}),
            'observedHistory':(ev.get('wholeCareerEvidence') or {}).get('rateEvidence',{})})
    if sum(h['mark']=='◎' for h in horses)>1:
        raise ValueError('multiple revision honmei')
    body={'version':VERSION,'raceId':detail['id'],'raceDate':detail['date'],
          'modelVersion':analysis['predictionModelVersion'],
          'modelHash':model.get('modelHash') if model else None,
          'inputSha256':input_hash(detail),'originalRecordsSha256':before,
          'analysisType':analysis['analysisType'],'analysisLabel':analysis['analysisLabel'],
          'predictionStatus':analysis['predictionStatus'],
          'probabilityModelStatus':analysis['probabilityModelStatus'],
          'productionEligible':analysis['productionEligible'],
          'honmeiDecision':analysis['honmeiDecision'],'horses':horses,
          'forecastText':analysis['forecastText'],'betPlan':analysis['recommendedBetPlan'],
          'scenarioSummaries':[{'id':s['id'],'label':s['label'],'assumptionStatus':s['assumptionStatus']} for s in scenario]}
    body['revisionId']=digest(body)
    body['createdAt']=at or datetime.now(timezone.utc).isoformat()
    out=deepcopy(detail)
    revisions=deepcopy(out.get('forecastRevisions') or [])
    prior=next((r for r in revisions if r.get('revisionId')==body['revisionId']),None)
    if prior is None:revisions.append(body)
    out['forecastRevisions']=revisions
    out['currentForecastRevisionId']=body['revisionId']
    if originals_hash(out)!=before:
        raise AssertionError('pre-off originals were changed')
    return out


def preserve_revisions(previous, incoming):
    """Retain immutable history across live refreshes and reject divergent chains."""
    out=deepcopy(incoming)
    old=previous.get('forecastRevisions') or []
    proposed=out.get('forecastRevisions') or []
    if proposed[:len(old)]!=old:
        if proposed:
            raise ValueError('forecast revision history prefix changed')
        out['forecastRevisions']=deepcopy(old)
        if previous.get('currentForecastRevisionId'):
            out['currentForecastRevisionId']=previous['currentForecastRevisionId']
    if out.get('currentForecastRevisionId') and latest_revision(out) is None:
        raise ValueError('current forecast revision pointer is invalid')
    return out
