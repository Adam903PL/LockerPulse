import { PointDetailPage } from "@/components/point-detail-page";

type PointPageProps = {
  params: Promise<{
    country: string;
    name: string;
  }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export default async function PointPage({ params, searchParams }: PointPageProps) {
  const [{ country, name }, query] = await Promise.all([params, searchParams]);

  return (
    <PointDetailPage
      country={country}
      name={name}
      returnQuery={first(query.q)}
      returnLat={first(query.lat)}
      returnLng={first(query.lng)}
      returnRadiusM={parseRadius(first(query.radius_m))}
      demoMode={parseDemo(first(query.demo))}
    />
  );
}

function first(value: string | string[] | undefined) {
  return Array.isArray(value) ? value[0] : value;
}

function parseRadius(value: string | undefined) {
  const radius = Number(value);
  if (!Number.isFinite(radius) || radius < 100 || radius > 50_000) {
    return 3000;
  }
  return radius;
}

function parseDemo(value: string | undefined) {
  return value === "true" || value === "1";
}
