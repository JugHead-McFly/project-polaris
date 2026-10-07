"""Local-only browser fixture. Run: python tests/serve_import_plan_fixture.py.

Real dashboard/assets and API routes, synthetic authentication and sky inputs.
Database exists only in memory and is discarded when the process exits.
This module is not imported by the production application.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import uvicorn
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.testclient import TestClient

from import_plan_fixture import ALICE, workflow, manifest
from app.api.hosted_account import router as account_router
from app.api.rig_profiles import router as rig_router


def add_browser_fixture(flow):
    app = flow.app
    app.include_router(account_router)
    app.include_router(rig_router)
    app.mount("/operator-assets", StaticFiles(directory=ROOT / "app/web"))

    @app.get("/operator", response_class=HTMLResponse)
    def dashboard():
        config = {"mode": "supabase", "supabaseUrl": "http://127.0.0.1",
                  "supabasePublishableKey": "synthetic-not-a-key"}
        stub = """<script>window.supabase={createClient:()=>({auth:{
          onAuthStateChange:()=>{},
          getSession:async()=>({data:{session:{access_token:'synthetic-not-a-token',
            user:{email:'synthetic@example.invalid'}}}})
        }})};</script>"""
        html = (ROOT / "app/web/operator.html").read_text(encoding="utf-8")
        html = (html.replace("__POLARIS_AUTH_CONFIG__", json.dumps(config))
                .replace("__SUPABASE_CLIENT_SCRIPT__", stub)
                .replace("__SCRIPT_NONCE__", "synthetic")
                .replace("__ASSET_VERSION__", "synthetic"))
        return HTMLResponse(html, headers={"Cache-Control": "no-store",
            "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'"})

    @app.get("/fixture", response_class=HTMLResponse)
    def controls():
        return """<h1>Synthetic import → next plan fixture</h1>
        <p>Memory database only. No telescope, NAS, Supabase, or weather access.</p>
        <form method="post" action="/fixture/import"><button>Import 3 hours M27</button></form>
        <form method="post" action="/fixture/complete"><button>Complete M27 goal</button></form>
        <a href="/operator">Open synthetic dashboard</a>"""

    def ingest(payload):
        with TestClient(app) as client:
            result = flow.sync(client, payload, ALICE)
            assert result.status_code == 200, result.text
        return RedirectResponse("/fixture", status_code=303)

    @app.post("/fixture/import")
    def partial():
        return ingest(manifest(3))

    @app.post("/fixture/complete")
    def complete():
        return ingest(manifest(2, "second"))


if __name__ == "__main__":
    with workflow() as flow:
        add_browser_fixture(flow)
        uvicorn.run(flow.app, host="127.0.0.1", port=8107, access_log=False)
