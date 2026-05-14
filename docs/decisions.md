# Technical Decisions

## Stage 1 scope

LockerPulse starts as a Smart Finder, not a full monitoring platform. The assignment rewards a focused, working interpretation of a vague brief, so stage 1 helps users choose the best nearby InPost point instead of trying to ingest and analyze the whole European network.

## Data handling

The backend queries the live InPost API for every search and optionally persists normalized points in Postgres. It does not crawl all points, create alerts, or build historical reliability until a collector exists.

## Scoring

The score is deliberately explainable. Every score includes reasons and warnings so the UI can show why a point was recommended. `locker_availability=NO_DATA` is surfaced as a caveat because the API often lacks occupancy data.

## Backend stack

FastAPI keeps the API small and readable. Prisma Client Python is used to match the project constraint, but persistence is optional at runtime so API exploration and UI development are not blocked by local database setup.
