"""The doctor workspace's Back to top button, checked in a real browser in REAL time.

Headless Edge with --virtual-time-budget (how render-harness.html is normally run) does not
run smooth scrolling or CSS transitions and does not reliably deliver scroll events, so it
cannot say whether the button appears, scrolls and vanishes. This drives headless Edge over
the DevTools protocol instead, with real waits.

Setup, as for render-harness.html: copy it to app/api/static/_harness.html (and axe-core to
_axe.js), serve app/api on 127.0.0.1:8765, then run this with the project's Python. Delete
the _harness/_axe files from app/api/static afterwards — they must never be committed or
built into the image.

Prints each step and a last line HEALTHY or BROKEN: <what failed>; exits 1 when broken.
"""
import asyncio
import json
import socket
import subprocess
import sys
import tempfile
import time

import requests
import websockets

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
URL = "http://127.0.0.1:8765/static/_harness.html?pane=overview&flow=totopready&vh=1"
FRAME = "document.getElementById('frame').contentWindow"

# Runs in the harness page; the app is in its iframe.
PROBE = f"""(() => {{
  const w = {FRAME}, d = w.document;
  const b = d.querySelector('#doctorToTopBtn'), s = d.querySelector('#doctorDashboardView .doctor-ai-content');
  const r = b.getBoundingClientRect();
  return {{scrollTop: Math.round(s.scrollTop), on: b.classList.contains('is-visible'),
    visible: w.getComputedStyle(b).visibility === 'visible',
    inside: r.right <= w.innerWidth && r.bottom <= w.innerHeight && r.width >= 44 && r.height >= 44,
    focusOnContent: d.activeElement === s}};
}})()"""
AXE = f"""(async () => {{
  const w = {FRAME}, d = w.document;
  if (!w.axe) {{
    await new Promise((ok, fail) => {{
      const t = d.createElement('script'); t.src = '/static/_axe.js'; t.onload = ok; t.onerror = fail;
      d.head.appendChild(t);
    }});
  }}
  const result = await w.axe.run(d.querySelector('#doctorToTopBtn'));
  return result.violations.map((v) => v.id);
}})()"""


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


async def run(width):
    port = _free_port()
    profile = tempfile.mkdtemp(prefix="edge-cdp-")
    edge = subprocess.Popen([EDGE, "--headless=new", "--disable-gpu", "--no-first-run",
                             f"--remote-debugging-port={port}", f"--user-data-dir={profile}",
                             f"--window-size={width},900", "about:blank"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    failures = []
    try:
        page = None
        for _ in range(150):
            try:
                page = next(t for t in requests.get(f"http://127.0.0.1:{port}/json", timeout=1).json()
                            if t["type"] == "page")
                break
            except Exception:
                time.sleep(0.2)
        if page is None:
            return [f"{width}px: Edge did not open its DevTools port"]
        async with websockets.connect(page["webSocketDebuggerUrl"], max_size=2**24) as ws:
            counter = 0

            async def evaluate(expression):
                nonlocal counter
                counter += 1
                await ws.send(json.dumps({"id": counter, "method": "Runtime.evaluate", "params": {
                    "expression": expression, "returnByValue": True, "awaitPromise": True}}))
                while True:
                    reply = json.loads(await ws.recv())
                    if reply.get("id") == counter:
                        return reply["result"]["result"].get("value")

            counter += 1
            await ws.send(json.dumps({"id": counter, "method": "Page.navigate", "params": {"url": URL}}))
            for _ in range(150):
                await asyncio.sleep(0.2)
                if "READY" in str(await evaluate("(document.getElementById('out')||{}).textContent")):
                    break

            def expect(step, state, **wanted):
                print(f"  {width}px {step:13} {state}")
                for key, value in wanted.items():
                    ok = value(state[key]) if callable(value) else state[key] == value
                    if not ok:
                        failures.append(f"{width}px {step}: {key}={state[key]}")

            scroller = f"{FRAME}.document.querySelector('#doctorDashboardView .doctor-ai-content')"
            expect("at top", await evaluate(PROBE), on=False, visible=False)
            await evaluate(f"{scroller}.scrollTop = 1200")
            await asyncio.sleep(0.6)
            expect("scrolled down", await evaluate(PROBE), on=True, visible=True, inside=True)
            violations = await evaluate(AXE)
            print(f"  {width}px axe on the button: {violations}")
            if violations:
                failures.append(f"{width}px axe: {violations}")
            await evaluate(f"{FRAME}.document.querySelector('#doctorToTopBtn').click()")
            await asyncio.sleep(0.15)
            expect("mid scroll", await evaluate(PROBE), scrollTop=lambda v: 0 < v < 1200)
            await asyncio.sleep(1.5)
            expect("after click", await evaluate(PROBE), scrollTop=0, on=False, visible=False, focusOnContent=True)
            await evaluate(f"{FRAME}.showDoctorView('upcoming')")
            await evaluate(f"{scroller}.scrollTop = 900")
            await asyncio.sleep(0.6)
            expect("other pane", await evaluate(PROBE), on=True, visible=True)
    finally:
        # The whole tree: Edge's helper processes outlive its launcher otherwise.
        subprocess.run(["taskkill", "/PID", str(edge.pid), "/T", "/F"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return failures


failures = [f for width in (1280, 390) for f in asyncio.run(run(width))]
print("HEALTHY" if not failures else "BROKEN: " + "; ".join(failures))
sys.exit(1 if failures else 0)
