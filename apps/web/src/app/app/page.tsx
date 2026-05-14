import { LockerPulseApp } from "@/components/locker-pulse-app";
import type { Coordinates } from "@/types/points";

type AppPageProps = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export default async function AppPage({ searchParams }: AppPageProps) {
  const params = await searchParams;
  const query = first(params.q);
  const coordinates = parseCoordinates(first(params.lat), first(params.lng));
  const radiusM = parseRadius(first(params.radius_m));
  const demoMode = parseDemo(first(params.demo));

  return (
    <LockerPulseApp
      initialQuery={query ?? ""}
      initialCoordinates={coordinates}
      initialRadiusM={radiusM}
      initialDemoMode={demoMode}
    />
  );
}

function first(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

function parseCoordinates(latValue?: string, lngValue?: string): Coordinates | null {
  const lat = Number(latValue);
  const lng = Number(lngValue);

  if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
    return null;
  }

  if (lat < -90 || lat > 90 || lng < -180 || lng > 180) {
    return null;
  }

  return { lat, lng };
}

function parseRadius(value?: string) {
  const radius = Number(value);
  if (!Number.isFinite(radius) || radius < 100 || radius > 50_000) {
    return 3000;
  }
  return radius;
}

function parseDemo(value?: string) {
  return value === "true" || value === "1";
}
