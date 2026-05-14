import argparse
import asyncio
import logging

from locker_pulse_api.config import get_settings
from locker_pulse_api.repositories.db import connect_database, disconnect_database
from locker_pulse_api.repositories.point_repository import PointRepository
from locker_pulse_api.services.report_triage import ReportTriageService
from locker_pulse_api.services.report_triage_engines import build_report_triage_engine


logger = logging.getLogger(__name__)


async def analyze_pending(*, limit: int, include_failed: bool) -> int:
    settings = get_settings()
    db = await connect_database(settings)
    if db is None:
        raise RuntimeError("Report triage requires DATABASE_URL and a generated Prisma client.")

    try:
        service = ReportTriageService(
            point_repository=PointRepository(db),
            triage_engine=build_report_triage_engine(
                provider=settings.report_triage_provider,
                model_name=settings.report_triage_model,
                api_base=settings.effective_report_triage_api_base,
                timeout_seconds=settings.report_triage_timeout_seconds,
                allow_cloud_photos=settings.report_triage_allow_cloud_photos,
                local_model_prefixes=settings.triage_local_model_prefixes,
            ),
            prompt_version=settings.report_triage_prompt_version,
        )
        return await service.analyze_pending(limit=limit, include_failed=include_failed)
    finally:
        await disconnect_database(db)


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze pending LockerPulse user reports with configured triage.")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--pending-only", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    count = asyncio.run(analyze_pending(limit=args.limit, include_failed=not args.pending_only))
    logger.info("Analyzed %s report(s).", count)


if __name__ == "__main__":
    main()
