"""Owned definitions, installed in the original app context by components.runtime.

The migration bridge preserves existing global state, decorators and monkeypatch
contracts. These definitions are not independently initialized modules yet.
"""

@app.get("/arvexq-icon-v175-{size}.png")
def arvexq_icon(size: int):
    if str(size) not in ARVEXQ_ICONS:raise HTTPException(status_code=404,detail="icon not found")
    return Response(base64.b64decode(ARVEXQ_ICONS[str(size)]),media_type="image/png",headers={"Cache-Control":"public,max-age=86400"})

@app.get("/arvexq-touch-v175.png")
def arvexq_touch_icon():
    return Response(ARVEXQ_TOUCH_ICON_180,media_type="image/png",headers={"Cache-Control":"no-store,max-age=0"})

@app.get("/manifest-v86.webmanifest")
@app.get("/manifest-arvexq-v175.webmanifest")
@app.get("/manifest-arvexq-v173.webmanifest")
@app.get("/manifest-arvexq-v130.webmanifest")
@app.get("/manifest-arvexq-v88.webmanifest")
def manifest():
    return Response(MANIFEST, media_type="application/manifest+json", headers={"Cache-Control":"public, max-age=3600"})

@app.get("/sw-v324-reset.js")
@app.get("/sw-v321-reset.js")
@app.get("/sw-v320-reset.js")
@app.get("/sw-v319-reset.js")
@app.get("/sw-v318-reset.js")
@app.get("/sw.js")
def service_worker():
    return Response(SW, media_type="application/javascript", headers={"Service-Worker-Allowed":"/", "Cache-Control":"no-store, max-age=0"})
