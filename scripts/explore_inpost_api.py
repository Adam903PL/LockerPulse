from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import httpx


API_URL = "https://api-global-points.easypack24.net/v1/points"
WARSAW = (52.2297, 21.0122)


def main() -> None:
    rows: list[str] = []
    rows.append("# InPost API Exploration\n")
    rows.append("Generated from live requests against `https://api-global-points.easypack24.net/v1/points`.\n")

    with httpx.Client(timeout=20) as client:
        global_payload = fetch(client, {"per_page": 1})
        rows.append(f"- Global points reported by API: `{global_payload.get('count')}`.")

        pl_payload = fetch(client, {"country": "PL", "per_page": 1})
        rows.append(f"- Poland points reported by API: `{pl_payload.get('count')}`.")

        nearby = fetch(
            client,
            {
                "relative_point": f"{WARSAW[0]},{WARSAW[1]}",
                "max_distance": 3000,
                "sort_by": "distance_to_relative_point",
                "country": "PL",
                "type": "parcel_locker_only",
                "per_page": 100,
                "page": 1,
            },
        )
        items = nearby.get("items", [])
        rows.append(f"- Warsaw 3 km parcel locker sample: `{len(items)}` items, upstream count `{nearby.get('count')}`.")
        rows.append(counter_line("Statuses", Counter(item.get("status") for item in items)))
        rows.append(
            counter_line(
                "Locker availability",
                Counter((item.get("locker_availability") or {}).get("status") for item in items),
            )
        )
        rows.append(counter_line("24/7", Counter(item.get("location_247") for item in items)))
        rows.append(counter_line("Easy access", Counter(item.get("easy_access_zone") for item in items)))
        rows.append(counter_line("Physical types", Counter(item.get("physical_type") for item in items)))

        filtered = fetch(
            client,
            {
                "relative_point": f"{WARSAW[0]},{WARSAW[1]}",
                "max_distance": 50_000,
                "sort_by": "distance_to_relative_point",
                "country": "PL",
                "type": "parcel_locker_only",
                "status": "Operating",
                "per_page": 5,
            },
        )
        rows.append(f"- `status=Operating` and `max_distance=50000` work together; sample count `{filtered.get('count')}`.")

        rows.append("\n## Product implications\n")
        rows.append("- The API is useful for nearby search and metadata-rich ranking.")
        rows.append("- `locker_availability.status` frequently returns `NO_DATA`, so LockerPulse treats it as a data caveat, not as a failure.")
        rows.append("- Stage 1 should avoid pretending to know real occupancy or long-term reliability before a collector exists.")
        rows.append("- The API supports enough location filtering to avoid importing the whole network for an internship-sized MVP.")

    Path("docs").mkdir(exist_ok=True)
    Path("docs/api-exploration.md").write_text("\n".join(rows) + "\n", encoding="utf-8")
    print("Wrote docs/api-exploration.md")


def fetch(client: httpx.Client, params: dict[str, Any]) -> dict[str, Any]:
    response = client.get(API_URL, params=params)
    response.raise_for_status()
    return response.json()


def counter_line(label: str, counter: Counter[Any]) -> str:
    values = ", ".join(f"`{key}`: `{count}`" for key, count in counter.most_common(8))
    return f"- {label}: {values}."


if __name__ == "__main__":
    main()
