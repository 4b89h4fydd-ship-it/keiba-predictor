"""Owned definitions, installed in the original app context by components.runtime.

The migration bridge preserves existing global state, decorators and monkeypatch
contracts. These definitions are not independently initialized modules yet.
"""

@app.get("/arvexq-racing-detail.webp")
def cinematic_detail_photo():
    return Response(CINEMATIC_DETAIL_WEBP,media_type="image/webp",headers={"Cache-Control":"public,max-age=86400"})

@app.get("/arvexq-racing-hero.webp")
def cinematic_hero():
    return Response(CINEMATIC_HERO_WEBP,media_type="image/webp",headers={"Cache-Control":"public,max-age=86400"})

@app.get("/arvexq-logo.webp")
def arvexq_logo():
    return Response(ARVEXQ_LOGO_WEBP,media_type="image/webp",headers={"Cache-Control":"public,max-age=31536000,immutable"})

@app.get("/hero-horse.webp")
def hero_horse():
    return Response(HERO_HORSE_WEBP, media_type="image/webp", headers={"Cache-Control":"public, max-age=86400"})

@app.get("/pace-preview.webp")
def pace_preview():
    return Response(PACE_PREVIEW_WEBP, media_type="image/webp", headers={"Cache-Control":"public, max-age=86400"})

@app.get("/styles-arvexq-v324.css")
@app.get("/styles-arvexq-v321.css")
@app.get("/styles-arvexq-v320.css")
@app.get("/styles-arvexq-v319.css")
@app.get("/styles-arvexq-v318.css")
@app.get("/styles-arvexq-v317.css")
@app.get("/styles-arvexq-v316.css")
@app.get("/styles-arvexq-v315.css")
@app.get("/styles-arvexq-v314.css")
@app.get("/styles-arvexq-v313.css")
@app.get("/styles-arvexq-v312.css")
@app.get("/styles-arvexq-v308.css")
@app.get("/styles-arvexq-v307.css")
@app.get("/styles-arvexq-v306.css")
@app.get("/styles-arvexq-v305.css")
@app.get("/styles-arvexq-v303.css")
@app.get("/styles-arvexq-v130.css")
@app.get("/styles-arvexq-v91.css")
@app.get("/styles-arvexq-v88.css")
@app.get("/styles-v86.css")
def styles(request: Request):
    current=request.url.path=="/styles-arvexq-v324.css"
    cache="public, max-age=31536000, immutable" if current else "no-cache, must-revalidate"
    return Response(CSS, media_type="text/css", headers={"Cache-Control":cache})
