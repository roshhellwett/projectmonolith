import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from gateway import app as _app  # noqa: F401 - re-exported for uvicorn main:app

if __name__ == "__main__":
    import uvicorn

    from core.config import PORT

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=PORT,
        log_level="info",
        access_log=False,
        server_header=False,
    )
