"""Worker process: `python -m app.jobs.worker`. Run several for more throughput."""

from __future__ import annotations

import asyncio
import logging
import signal

from .queue import run_one

log = logging.getLogger("preproom.worker")


async def main(poll_s: float = 0.5) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:  # Windows
            pass
    log.info("worker started")
    while not stop.is_set():
        try:
            worked = await run_one()
        except Exception:  # noqa: BLE001 - e.g. database restarting; keep the worker alive
            log.exception("worker loop error")
            worked = False
        if not worked:
            try:
                await asyncio.wait_for(stop.wait(), timeout=poll_s)
            except TimeoutError:
                pass
    log.info("worker stopped")


if __name__ == "__main__":
    asyncio.run(main())
