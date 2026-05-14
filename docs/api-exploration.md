# InPost API Exploration

Generated from live requests against `https://api-global-points.easypack24.net/v1/points`.

- Global points reported by API: `153441`.
- Poland points reported by API: `33986`.
- Warsaw 3 km parcel locker sample: `25` items, upstream count `25`.
- Statuses: `Operating`: `21`, `Created`: `4`.
- Locker availability: `NO_DATA`: `25`.
- 24/7: `True`: `22`, `False`: `3`.
- Easy access: `True`: `25`.
- Physical types: `newfm`: `20`, `modular`: `3`, `screenless`: `2`.
- `status=Operating` and `max_distance=50000` work together; sample count `25`.

## Product implications

- The API is useful for nearby search and metadata-rich ranking.
- `locker_availability.status` frequently returns `NO_DATA`, so LockerPulse treats it as a data caveat, not as a failure.
- Stage 1 should avoid pretending to know real occupancy or long-term reliability before a collector exists.
- The API supports enough location filtering to avoid importing the whole network for an internship-sized MVP.
