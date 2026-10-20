"""Read-only GitHub Actions v4 artifact witness using server-returned times/digest.

An artifact authenticates availability of exact bytes, not official race-data
truth, full-calendar coverage, or scientific independence of model design.
"""
from datetime import datetime, timezone
from hashlib import sha256
import io
import json
import os
import re
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request, build_opener, HTTPRedirectHandler, urlopen
import zipfile

from arvexq.research.stage63.forward import canonical, digest
from .protocol import check_plan, post_at, verify_local, JST

REPO="4b89h4fydd-ship-it/keiba-predictor"
REPO_ID=1386943133
LIMIT=50*1024*1024


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class GitHubArtifacts:
    """No race endpoint, DB access, writes, retry loop or caller-provided URL."""
    def __init__(self, token=None):
        self.token=token if token is not None else os.environ.get("GITHUB_TOKEN")

    def _request(self, suffix):
        headers={"Accept":"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28",
                 "User-Agent":"ARVEXQ-research-witness"}
        if self.token:headers["Authorization"]="Bearer "+self.token
        return Request("https://api.github.com/repos/"+REPO+"/"+suffix,headers=headers)

    def metadata(self, artifact_id):
        if type(artifact_id) is not int or artifact_id<=0:raise ValueError("invalid artifact ID")
        with urlopen(self._request("actions/artifacts/"+str(artifact_id)),timeout=30) as response:
            return json.load(response)

    def run(self, run_id):
        if type(run_id) is not int or run_id<=0:raise ValueError("invalid run ID")
        with urlopen(self._request("actions/runs/"+str(run_id)),timeout=30) as response:
            return json.load(response)

    def archive(self, artifact_id):
        request=self._request("actions/artifacts/"+str(artifact_id)+"/zip")
        try:
            with build_opener(NoRedirect).open(request,timeout=30) as response:
                return self._bounded(response)
        except HTTPError as error:
            if error.code!=302:raise
            location=error.headers.get("Location","")
        parsed=urlparse(location)
        host=parsed.hostname or ""
        if parsed.scheme!="https" or not (host.endswith(".blob.core.windows.net") or
                host.endswith(".githubusercontent.com") or host.endswith(".actions.githubusercontent.com")):
            raise ValueError("unapproved artifact redirect")
        # Fresh request deliberately has no Authorization header on storage host.
        with urlopen(Request(location),timeout=30) as response:
            return self._bounded(response)

    @staticmethod
    def _bounded(response):
        raw=response.read(LIMIT+1)
        if len(raw)>LIMIT:raise ValueError("artifact too large")
        return raw


def instant(text):
    result=datetime.fromisoformat(text.replace("Z","+00:00"))
    if result.tzinfo is None:raise ValueError("server timestamp lacks timezone")
    return result


def read_witness(client, artifact_id, *, before, source_member=None):
    """client defaults to live GitHub REST in the CLI, never a JSON manifest."""
    meta=client.metadata(artifact_id)
    run=client.run(meta["workflow_run"]["id"])
    if meta["id"]!=artifact_id or meta.get("expired") is not False:
        raise ValueError("artifact identity/expiry")
    if run.get("repository",{}).get("id")!=REPO_ID or run.get("repository",{}).get("full_name")!=REPO:
        raise ValueError("untrusted repository")
    if meta["workflow_run"].get("repository_id")!=REPO_ID or meta["workflow_run"].get("head_repository_id")!=REPO_ID:
        raise ValueError("fork/foreign artifact")
    if run.get("id")!=meta["workflow_run"]["id"] or run.get("head_sha")!=meta["workflow_run"].get("head_sha"):
        raise ValueError("artifact/run binding mismatch")
    if run.get("status")!="completed" or run.get("conclusion")!="success":
        raise ValueError("successful completed workflow required")
    # Completion is a conservative upper bound on artifact availability.
    times=[instant(meta[k]) for k in ("created_at","updated_at")]
    times += [instant(run[k]) for k in ("created_at","updated_at")]
    if max(times)>=before:
        raise ValueError("external witness not completed before deadline")
    if times[0]>times[1] or times[2]>times[3] or times[0]<times[2] or times[1]>times[3]:
        raise ValueError("inconsistent server chronology")
    expected=meta.get("digest")
    if not isinstance(expected,str) or not re.fullmatch(r"sha256:[a-f0-9]{64}",expected):
        raise ValueError("missing GitHub v4 artifact digest")
    raw=client.archive(artifact_id)
    if len(raw)>LIMIT or "sha256:"+sha256(raw).hexdigest()!=expected:
        raise ValueError("artifact bytes differ from authenticated digest")
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        members=z.infolist()
        if source_member is None:
            if len(members)!=1 or members[0].filename!="bundle.json" or members[0].file_size>LIMIT:
                raise ValueError("expected sole bounded bundle.json")
            selected=members[0]
        else:
            if not isinstance(source_member,str) or source_member.startswith("/") or ".." in source_member.split("/"):
                raise ValueError("invalid saved source member")
            matching=[m for m in members if m.filename==source_member]
            if len(matching)!=1 or matching[0].file_size>LIMIT:
                raise ValueError("missing/duplicate/oversized saved source member")
            selected=matching[0]
        payload=json.loads(z.read(selected))
    return payload,{"artifactId":artifact_id,"artifactDigest":expected,
                    "runId":run["id"],"headSha":run["head_sha"],
                    "serverObservedBy":max(times).isoformat(),
                    "url":"https://github.com/"+REPO+"/actions/runs/"+str(run["id"])}


def verify_batch(client, plan_artifact_id, forecast_artifact_id):
    # Plan must be preregistered before the fixed cohort opens.
    # First obtain plan using current time as a bounded read, then enforce opening.
    plan_bundle, plan_anchor=read_witness(client,plan_artifact_id,before=datetime.now(timezone.utc))
    plan=plan_bundle["plan"]
    check_plan(plan)
    opening=datetime.fromisoformat(plan["startDate"]+"T00:00:00").replace(tzinfo=JST)
    if instant(plan_anchor["serverObservedBy"])>=opening:
        raise ValueError("plan was not preregistered before cohort")
    batch, forecast_anchor=read_witness(client,forecast_artifact_id,before=datetime.now(timezone.utc))
    if plan_artifact_id==forecast_artifact_id or batch.get("schema")!="arvexq-stage64-batch-1" or batch["planSha256"]!=digest(plan):
        raise ValueError("independent plan/forecast binding required")
    receipts=batch["receipts"]
    ids=[r["snapshot"]["raceId"] for r in receipts]
    if not ids or len(set(ids))!=len(ids) or sorted(ids)!=batch["cohort"]:
        raise ValueError("duplicate/incomplete frozen cohort")
    for receipt in receipts:
        verify_local(receipt,plan)
        off=post_at(receipt["snapshot"]["input"])
        if instant(forecast_anchor["serverObservedBy"])>=off:
            raise ValueError("forecast bytes were witnessed after off")
        if instant(plan_anchor["serverObservedBy"])>=instant(receipt["snapshot"]["capturedAt"]):
            raise ValueError("forecast predates witnessed plan")
        if instant(receipt["snapshot"]["capturedAt"])>instant(forecast_anchor["serverObservedBy"]):
            raise ValueError("local capture later than server witness")
    return {"plan":plan,"batch":batch,"anchors":{"plan":plan_anchor,"forecast":forecast_anchor},
            "independentlyVerifiedPreoff":True,
            "scope":"Exact frozen submitted cohort bytes available before off; no whole-calendar or official-data claim."}
