"""Owned definitions, installed in the original app context by components.runtime.

The migration bridge preserves existing global state, decorators and monkeypatch
contracts. These definitions are not independently initialized modules yet.
"""

@app.get("/", response_class=HTMLResponse)
@app.get("/venue", response_class=HTMLResponse)
@app.get("/race", response_class=HTMLResponse)
def home():
    # Keep first paint light. Race list/detail data is loaded from Cloudflare/D1
    # by the browser; Render remains the fallback for live/manual refreshes.
    boot='<script>window.__ARVEXQ_BOOTSTRAP__=null;</script>'
    html=INDEX.replace(
        '<script src="/app-v324.js"></script>',
        boot+'\n<script src="/app-v324.js"></script>'
    )
    return HTMLResponse(html, headers={
        "Cache-Control":"no-store, no-cache, must-revalidate, max-age=0",
        "Pragma":"no-cache","Expires":"0"
    })
