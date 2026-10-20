"""Owned definitions, installed in the original app context by components.runtime.

The migration bridge preserves existing global state, decorators and monkeypatch
contracts. These definitions are not independently initialized modules yet.
"""

def _fetch_nar_payouts_only(detail: dict) -> tuple[list[dict],str]:
    code=NAR_BABA_CODES.get(detail.get("track"))
    if not code:return [],"競馬場コード未取得"
    query=urllib.parse.urlencode({
        "k_babaCode":code,
        "k_raceDate":str(detail.get("date") or "").replace("-","/"),
        "k_raceNo":int(detail.get("raceNumber") or 0),
    })
    urls=[
        "https://www.keiba.go.jp/KeibaWebSP/TodayRaceInfo/S_RefundMoneyList?"+query,
        "https://sp.keiba.go.jp/KeibaWebSP/TodayRaceInfo/S_RefundMoneyList?"+query,
    ]
    last=""
    for url in urls:
        try:
            req=urllib.request.Request(url,headers={
                "User-Agent":"Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Safari/604.1",
                "Accept-Language":"ja,en-US;q=0.8",
            })
            with urllib.request.urlopen(req,timeout=float(os.getenv("NAR_PAYOUT_TIMEOUT_SEC","2.0"))) as response:
                html=_jra_decode(response.read())
            payouts=_parse_payouts(BeautifulSoup(html,"html.parser"))
            if payouts:return payouts,url
            last="払戻表は取得したが解析結果0件"
        except Exception as exc:
            last=str(exc)
    return [],last or "払い戻し未取得"

def _attach_nar_payouts(detail: dict) -> dict:
    result=detail.get("result")
    if not isinstance(result,dict):
        result={}
        detail["result"]=result
    if result.get("payouts"):return detail
    payouts,source=_fetch_nar_payouts_only(detail)
    if payouts:
        result["payouts"]=payouts
        result["status"]="確定"
        result["payoutSource"]="NAR公式"
        result["payoutUrl"]=source
        result.pop("payoutError",None)
    else:
        result["payoutError"]="払い戻し未取得"
        result["payoutDebug"]=source[:240]
    return detail
