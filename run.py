"""
Start the FastAPI server.

On Windows, the default ProactorEventLoop has a known incompatibility with aiohttp
(used by the Azure Storage SDK) that causes WinError 995 and server crashes.
Setting WindowsSelectorEventLoopPolicy HERE — before uvicorn creates the event loop —
is the only reliable place to apply it.
"""
import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.api.main:app",
        host="0.0.0.0",
        port=8010,
        reload=False,
    )
