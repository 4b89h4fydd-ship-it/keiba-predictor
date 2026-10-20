"""Read-only Cloudflare deployment workflow contract. NEVER triggers deployment."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WORKFLOWS = (
    ".github/workflows/arvexq-api-storage-deploy.yml",
    ".github/workflows/arvexq-web-deploy.yml",
)


def inspect_deploy_workflows():
    """Check existing workflow files without network, mutations or CI dispatch."""
    results = {}
    for filename in WORKFLOWS:
        path = ROOT / filename
        if not path.is_file():
            results[filename] = {"present": False, "content": False}
            continue
        source = path.read_text(encoding="utf-8")
        results[filename] = {"present": True, "content": bool(source.strip()),
                             "cloudflare_named": "cloudflare" in source.lower() or "wrangler" in source.lower()}
    return {"workflows": results, "production_verified": False,
            "deployment_executed": False}
