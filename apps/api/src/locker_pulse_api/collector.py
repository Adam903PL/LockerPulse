import argparse
import asyncio
import json
import logging
from pathlib import Path

from locker_pulse_api.clients.inpost import InPostClient
from locker_pulse_api.config import get_settings
from locker_pulse_api.repositories.db import connect_database, disconnect_database
from locker_pulse_api.repositories.point_repository import PointRepository
from locker_pulse_api.services.collector_service import CollectorService, CollectorTarget

logger = logging.getLogger(__name__)
DEFAULT_SEEDS_PATH = Path(__file__).resolve().parents[2] / "collector-seeds.json"


async def run_once(*, seeds_path: Path, max_pages: int | None = None) -> None:
    settings = get_settings()
    db = await connect_database(settings)
    if db is None:
        raise RuntimeError("Collector requires DATABASE_URL and a generated Prisma client.")

    try:
        targets = load_targets(seeds_path, max_pages=max_pages)
        service = CollectorService(
            InPostClient(settings),
            PointRepository(db),
        )
        summary = await service.collect_once(targets=targets)
        logger.info(
            "Collector run %s finished: %s points, %s snapshots, %s events in %sms",
            summary.collector_run_id,
            summary.point_count,
            summary.snapshot_count,
            summary.event_count,
            summary.duration_ms,
        )
    finally:
        await disconnect_database(db)


async def run_loop(*, seeds_path: Path, interval_seconds: int, max_pages: int | None) -> None:
    while True:
        await run_once(seeds_path=seeds_path, max_pages=max_pages)
        await asyncio.sleep(interval_seconds)


def load_targets(seeds_path: Path, *, max_pages: int | None = None) -> list[CollectorTarget]:
    payload = json.loads(seeds_path.read_text(encoding="utf-8"))
    targets: list[CollectorTarget] = []
    for item in payload["targets"]:
        target_max_pages = max_pages if max_pages is not None else item.get("max_pages", 1)
        targets.append(
            CollectorTarget(
                label=item["label"],
                lat=item.get("lat"),
                lng=item.get("lng"),
                radius_m=item.get("radius_m"),
                country=item.get("country", "PL"),
                point_type=item.get("point_type", "parcel_locker_only"),
                max_pages=target_max_pages,
            )
        )
    return targets


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect InPost point history for LockerPulse.")
    parser.add_argument("--loop", action="store_true", help="Run forever with a sleep interval.")
    parser.add_argument("--once", action="store_true", help="Run one collection pass and exit.")
    parser.add_argument("--interval-seconds", type=int, default=1800)
    parser.add_argument("--max-pages", type=int, default=None)
    parser.add_argument("--seeds", type=Path, default=DEFAULT_SEEDS_PATH)
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    args = parse_args()
    if args.loop and args.once:
        raise SystemExit("Use either --once or --loop, not both.")

    if args.loop:
        asyncio.run(
            run_loop(
                seeds_path=args.seeds,
                interval_seconds=args.interval_seconds,
                max_pages=args.max_pages,
            )
        )
        return

    asyncio.run(run_once(seeds_path=args.seeds, max_pages=args.max_pages))


if __name__ == "__main__":
    main()
