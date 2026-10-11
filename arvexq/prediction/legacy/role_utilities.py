"""Legacy calculations with explicit dependencies; formulas preserved."""
from __future__ import annotations

from arvexq.prediction.legacy_model_tables import (V212_P2_MODEL_COEFFICIENTS, V212_P2_MODEL_INTERCEPT, V213_BLEND, V213_FEATURES, V213_MEAN, V213_P1_COEF, V213_P2_COEF, V213_P3_COEF, V213_SCALE, V215_P1_BLEND)
from arvexq.prediction.legacy.role_features import _v213_feature_rows
from arvexq.prediction.legacy.common import _v213_softmax, _v213_zscore
from arvexq.prediction.legacy.professional import _v215_professional_p1
from arvexq.prediction.legacy.tactical import _v218_tactical_roles, V218_P1_BLEND


def _v213_role_utilities(detail: dict, horses: list[dict]):
    feats=_v213_feature_rows(detail,horses)
    def linear(f,coef):
        total=0.0
        for i,name in enumerate(V213_FEATURES):total += coef[i]*((f.get(name,.5)-V213_MEAN[i])/max(1e-9,V213_SCALE[i]))
        return total
    new1=[linear(f,V213_P1_COEF) for f in feats];new2=[linear(f,V213_P2_COEF) for f in feats];new3=[linear(f,V213_P3_COEF) for f in feats]
    cur2=[];cur3=[]
    for f in feats:
        p2f={'base':f['eval_score'],'perf':f['race_perf'],'rep':f['representative'],'dist':f['distance'],'track':f['track'],'going':f['going'],'level':f['level'],'jockey':f['jockey'],'trainer':f['trainer'],'body':f['body'],'lap':f['lap'],'ten':f['ten'],'early3':f['early3'],'moved3':f['moved3'],'front':f['front'],'stalk':f['stalk'],'mid':f['mid'],'close':f['close'],'evidence':f['evidence'],'data':f['data']}
        cur2.append(V212_P2_MODEL_INTERCEPT+sum(V212_P2_MODEL_COEFFICIENTS[k]*p2f[k] for k in V212_P2_MODEL_COEFFICIENTS))
        cur3.append(f['eval_score']*.14+f['race_perf']*.14+f['representative']*.14+f['distance']*.06+f['track']*.05+f['level']*.05+f['going']*.04+f['moved3']*.10+f['mid']*.07+f['close']*.08+f['lap']*.06+f['evidence']*.07)
    z1=_v213_zscore(new1);z2n=_v213_zscore(new2);z2c=_v213_zscore(cur2);z3n=_v213_zscore(new3);z3c=_v213_zscore(cur3)
    pro1=_v215_professional_p1(detail,horses,feats)
    v215_u1=[(1.0-V215_P1_BLEND)*z1[i]+V215_P1_BLEND*pro1[i] for i in range(len(horses))]
    tactical1,p2_role,p3_role,tactical_audit=_v218_tactical_roles(detail,horses,feats)
    u1=[(1.0-V218_P1_BLEND)*v215_u1[i]+V218_P1_BLEND*tactical1[i] for i in range(len(horses))]
    # Keep the validated v213 P2/P3 marginals untouched. v218 uses role compatibility
    # conditionally in the trifecta order engine rather than silently replacing them.
    u2=[(1.0-V213_BLEND[1])*z2c[i]+V213_BLEND[1]*z2n[i] for i in range(len(horses))]
    u3=[(1.0-V213_BLEND[2])*z3c[i]+V213_BLEND[2]*z3n[i] for i in range(len(horses))]
    return u1,u2,u3,_v213_softmax(u1),_v213_softmax(u2),_v213_softmax(u3),z1,pro1,tactical1,p2_role,p3_role,tactical_audit

