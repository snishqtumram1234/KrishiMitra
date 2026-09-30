"""Seed demo traffic so the metrics dashboard has real numbers (DEV ONLY).

Runs the cases in data/demo-cases/cases.json through a running backend's real HTTP API
(create case -> upload image -> analyze -> optional follow-up), then prints the metrics the server
computed from the routing_runs / model_runs those calls produced.

  # terminal 1 (memory store: data lives in this server process)
  uvicorn app.main:app
  # terminal 2
  python scripts/seed_demo.py --api http://127.0.0.1:8000

Needs SUPABASE_JWT_SECRET in backend/.env: the script mints local test tokens (3 farmers + 1 expert)
with it, exactly like scripts/dev_token.py, and refuses to run when ENVIRONMENT=production.

Images are synthetic (drawn with OpenCV) unless a case names a real photo in data/demo-cases/images/.
Routing, quality-gate, cost and latency numbers are real; vision predictions on synthetic pictures
are meaningless. Each run adds new cases; run it more than once and the totals grow.
"""

import argparse
import json
import sys
import time
import uuid
from collections import Counter
from pathlib import Path

import cv2
import httpx
import jwt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.config import get_settings  # noqa: E402

DEMO_DIR = Path(__file__).resolve().parents[2] / "data" / "demo-cases"
W, H = 640, 480


# ---------------------------------------------------------------- synthetic images
def _leaf(rng: np.random.Generator, hue=(50, 140, 60)) -> np.ndarray:
    img = np.full((H, W, 3), hue, np.float32) + rng.normal(0, 18, (H, W, 3))
    for x in range(0, W, 40):
        cv2.line(img, (x, 0), (W // 2, H // 2), (90, 190, 110), 2)
    return img


def _dots(img, rng, n, color, radius=(4, 12), halo=None):
    for _ in range(n):
        c = (int(rng.integers(20, W - 20)), int(rng.integers(20, H - 20)))
        r = int(rng.integers(*radius))
        if halo:
            cv2.circle(img, c, r + 5, halo, -1)
        cv2.circle(img, c, r, color, -1)


def synthetic_image(style: str, seed: int) -> bytes:
    rng = np.random.default_rng(seed)
    img = _leaf(rng)
    if style == "rust":
        _dots(img, rng, 120, (30, 100, 210), radius=(2, 5))  # orange pustules (BGR)
    elif style == "spots":
        _dots(img, rng, 18, (30, 60, 110), radius=(8, 20), halo=(40, 190, 200))  # brown spots, yellow halo
    elif style == "holes":
        _dots(img, rng, 14, (20, 40, 50), radius=(8, 22))
    elif style == "mixed":
        _dots(img, rng, 10, (30, 60, 110), radius=(6, 16), halo=(40, 190, 200))
        _dots(img, rng, 6, (20, 40, 50), radius=(6, 14))
    elif style == "field":
        img = _leaf(rng, hue=(60, 130, 70))
        for _ in range(200):
            x, y = int(rng.integers(0, W)), int(rng.integers(0, H))
            cv2.ellipse(img, (x, y), (30, 12), int(rng.integers(0, 180)), 0, 360,
                        (int(rng.integers(40, 80)), int(rng.integers(120, 190)), int(rng.integers(50, 100))), -1)
    elif style == "blurry":
        _dots(img, rng, 18, (30, 60, 110), radius=(8, 20))
        img = cv2.GaussianBlur(img, (31, 31), 0)
    elif style == "dark":
        img = img * 0.12
    elif style == "overexposed":
        img = img + 190
    elif style == "tiny":
        img = cv2.resize(img, (120, 90))
    elif style == "no_leaf":
        img = np.full((H, W, 3), (150, 120, 110), np.float32) + rng.normal(0, 25, (H, W, 3))
    elif style != "healthy":
        raise ValueError(f"unknown image style {style!r}")
    ok, buf = cv2.imencode(".jpg", np.clip(img, 0, 255).astype(np.uint8))
    assert ok
    return buf.tobytes()


def image_bytes(spec: dict, seed: int) -> tuple[bytes, str]:
    if "file" in spec:
        path = DEMO_DIR / "images" / spec["file"]
        return path.read_bytes(), f"real:{spec['file']}"
    return synthetic_image(spec["style"], seed), f"synthetic:{spec['style']}"


# ---------------------------------------------------------------- tokens + API
def token(sub: str, secret: str, expert: bool = False) -> dict:
    claims = {"sub": sub, "aud": "authenticated", "role": "authenticated", "exp": int(time.time()) + 3600}
    if expert:
        claims["app_metadata"] = {"role": "expert"}
    return {"Authorization": f"Bearer {jwt.encode(claims, secret, algorithm='HS256')}"}


class Api:
    def __init__(self, base: str, client: httpx.Client | None = None):
        self.http = client or httpx.Client(base_url=base.rstrip("/"), timeout=60)  # tests pass a TestClient

    def call(self, method: str, path: str, headers: dict, **kw) -> dict:
        r = self.http.request(method, path, headers=headers, **kw)
        if r.status_code >= 400:
            raise SystemExit(f"{method} {path} -> {r.status_code}: {r.text[:300]}")
        return r.json()

    def upload(self, case_id: str, headers: dict, kind: str, data: bytes) -> None:
        self.call("POST", f"/api/cases/{case_id}/images", headers, data={"kind": kind},
                  files={"file": ("demo.jpg", data, "image/jpeg")})


def run_case(api: Api, case: dict, headers: dict, index: int) -> dict:
    body = {"crop": "soybean", "district": case["district"], "language": case["language"],
            "symptom_context": case["symptom_context"], "description": "[demo]"}  # no routing keywords: description is part of the routed text
    for field in ("growth_stage", "recent_rainfall"):
        if case.get(field):
            body[field] = case[field]
    created = api.call("POST", "/api/cases", headers, json=body)
    cid = created["id"]
    if case.get("image"):
        data, _ = image_bytes(case["image"], seed=index)
        api.upload(cid, headers, "leaf_closeup", data)
    if case.get("field_overview"):
        data, _ = image_bytes(case["field_overview"], seed=1000 + index)
        api.upload(cid, headers, "field_overview", data)
    analysis = api.call("POST", f"/api/cases/{cid}/analyze", headers)
    result = {"id": case["id"], "state": analysis["state"], "path": analysis["result"]["path"],
              "reason": analysis["result"]["reason"], "run": analysis["routing_run_id"]}
    if fu := case.get("follow_up"):
        files = {}
        if fu.get("image"):
            data, _ = image_bytes(fu["image"], seed=2000 + index)
            files = {"file": ("followup.jpg", data, "image/jpeg")}
        again = api.call("POST", f"/api/cases/{cid}/follow-up", headers,
                         data={"answer": fu["answer"]} if fu.get("answer") else None, files=files or None)
        result |= {"follow_up_state": again["state"], "follow_up_path": again["result"]["path"]}
    return result


def mismatches(case: dict, res: dict) -> list[str]:
    out = []
    if case.get("expect_path") and res["path"] != case["expect_path"]:
        out.append(f"path {res['path']} (expected {case['expect_path']})")
    if case.get("expect_state") and res["state"] != case["expect_state"]:
        out.append(f"state {res['state']} (expected {case['expect_state']})")
    return out


def pct(rate: dict) -> str:
    return "n/a" if rate["rate"] is None else f"{rate['rate']:.0%} ({rate['numerator']}/{rate['denominator']})"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--api", default="http://127.0.0.1:8000")
    ap.add_argument("--cases", type=Path, default=DEMO_DIR / "cases.json")
    ap.add_argument("--limit", type=int, help="only the first N cases")
    ap.add_argument("--farmers", type=int, default=3)
    a = ap.parse_args()

    s = get_settings()
    if s.environment == "production":
        raise SystemExit("Refusing to seed demo data in production.")
    if not s.supabase_jwt_secret:
        raise SystemExit("Set SUPABASE_JWT_SECRET in backend/.env (and run the server with the same value).")

    cases = json.loads(a.cases.read_text(encoding="utf-8"))["cases"][: a.limit]
    farmers = [token(str(uuid.uuid4()), s.supabase_jwt_secret) for _ in range(a.farmers)]
    api = Api(a.api)
    print(f"Seeding {len(cases)} demo cases into {a.api} (synthetic images unless real ones are provided)\n")

    bad, states, paths = [], Counter(), Counter()
    started = time.perf_counter()
    for i, case in enumerate(cases):
        res = run_case(api, case, farmers[i % len(farmers)], i)
        states[res["state"]] += 1
        paths[res["path"]] += 1
        miss = mismatches(case, res)
        flag = "  !! " + "; ".join(miss) if miss else ""
        extra = f"  -> follow-up: {res['follow_up_path']}/{res['follow_up_state']}" if "follow_up_state" in res else ""
        print(f"{i + 1:>2}. {case['id']}  {res['path']:<22} {res['state']:<21} {case['symptom_context'][:38]!r}{extra}{flag}")
        if miss:
            bad.append((case["id"], miss))
    print(f"\nDone in {time.perf_counter() - started:.1f}s. "
          f"{len(cases) - len(bad)}/{len(cases)} matched their expected path/state.")
    for cid, miss in bad:
        print(f"  mismatch {cid}: {'; '.join(miss)}")

    expert = token(str(uuid.uuid4()), s.supabase_jwt_secret, expert=True)
    o = api.call("GET", "/api/metrics/overview", expert)
    r = api.call("GET", "/api/metrics/routes", expert)
    c = api.call("GET", "/api/metrics/cost-latency", expert)
    lat = o["latency_per_analysis"]
    print("\n================ metrics computed by the server from routing_runs / model_runs")
    print(f"cases / analyses        : {o['total_cases']} / {o['total_analyses']}")
    print(f"latency per analysis    : avg {lat['avg_ms']} ms, p50 {lat['p50_ms']} ms, p95 {lat['p95_ms']} ms")
    print(f"cost per case (est.)    : ${o['cost_per_case_usd']:.6f}   total ${o['cost_total_usd']:.6f}")
    print(f"escalation rate         : {pct(o['escalation_rate'])}")
    print(f"abstention rate         : {pct(o['abstention_rate'])}   (vision-only: {pct(o['vision_abstention_rate'])})")
    print(f"retrieval success rate  : {pct(o['retrieval_success_rate'])}")
    print(f"cache-hit rate (weather): {pct(o['cache_hit_rate'])}   sources {o['weather_sources']}")
    print(f"model disagreements     : {o['model_disagreement_count']}")
    print(f"vision model called in  : {pct(r['vision_call_rate'])} of analyses")
    print(f"estimated cost saved by skipping steps: ${r['estimated_cost_saved_usd']:.6f}")
    print("route distribution      : " + ", ".join(f"{p['path']} {p['share']:.0%}" for p in r["by_path"]))
    print("tier usage (calls)      : " + ", ".join(f"{t['tier']} {t['calls']}" for t in c["by_tier"]))
    for n in o["notes"] + c["notes"]:
        print(f"note: {n}")


if __name__ == "__main__":
    main()
