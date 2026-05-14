import { redirect } from "next/navigation";
import { LandingPage } from "@/components/landing-page";

type HomeProps = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

const LEGACY_APP_PARAMS = new Set(["q", "lat", "lng", "radius_m", "demo"]);

export default async function Home({ searchParams }: HomeProps) {
  const params = await searchParams;
  if (hasLegacyAppParams(params)) {
    const suffix = toSearchParams(params).toString();
    redirect(`/app${suffix ? `?${suffix}` : ""}`);
  }

  return <LandingPage />;
}

function hasLegacyAppParams(params: Record<string, string | string[] | undefined>) {
  return Object.keys(params).some((key) => LEGACY_APP_PARAMS.has(key));
}

function toSearchParams(params: Record<string, string | string[] | undefined>) {
  const next = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (Array.isArray(value)) {
      for (const item of value) {
        if (item != null) {
          next.append(key, item);
        }
      }
      continue;
    }
    if (value != null) {
      next.set(key, value);
    }
  }
  return next;
}
