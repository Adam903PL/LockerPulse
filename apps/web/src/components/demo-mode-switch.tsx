"use client";

import { useEffect } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { cn } from "@/lib/utils";

const DEMO_QUERY = "Strzyżewice 108, 23-107 Strzyżewice";
const DEMO_LAT = "51.0808";
const DEMO_LNG = "22.4416";
const DEMO_RADIUS_M = "3000";
const DEMO_MODE_STORAGE_KEY = "lockerpulse-demo-mode";

type DemoModeSwitchProps = {
  enabled: boolean;
  onChange?: (enabled: boolean) => void;
  compact?: boolean;
};

export function DemoModeSwitch({ enabled, onChange, compact = false }: DemoModeSwitchProps) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  useEffect(() => {
    if (enabled) {
      writePersistedDemoMode(true);
    }
  }, [enabled]);

  useEffect(() => {
    if (onChange || enabled || !readPersistedDemoMode()) {
      return;
    }

    const params = new URLSearchParams(searchParams.toString());
    params.set("demo", "true");
    if (pathname === "/" && (!params.get("lat") || !params.get("lng"))) {
      params.set("q", DEMO_QUERY);
      params.set("lat", DEMO_LAT);
      params.set("lng", DEMO_LNG);
      params.set("radius_m", DEMO_RADIUS_M);
    }
    router.replace(`${pathname}?${params.toString()}`);
  }, [enabled, onChange, pathname, router, searchParams]);

  function toggle() {
    const next = !enabled;
    writePersistedDemoMode(next);
    if (onChange) {
      onChange(next);
      return;
    }

    const params = new URLSearchParams(searchParams.toString());
    if (next) {
      params.set("demo", "true");
      if (pathname === "/" && (!params.get("lat") || !params.get("lng"))) {
        params.set("q", DEMO_QUERY);
        params.set("lat", DEMO_LAT);
        params.set("lng", DEMO_LNG);
        params.set("radius_m", DEMO_RADIUS_M);
      }
    } else {
      params.delete("demo");
      if (pathname === "/demo-history") {
        router.push("/");
        return;
      }
    }

    const suffix = params.toString();
    router.push(`${pathname}${suffix ? `?${suffix}` : ""}`);
  }

  return (
    <button
      type="button"
      role="switch"
      aria-checked={enabled}
      onClick={toggle}
      className={cn(
        "inline-flex items-center gap-2 rounded-full border px-2 py-1 text-xs font-black transition",
        enabled
          ? "border-[#ffd200] bg-[#ffd200] text-[#1d1d1b] shadow-sm"
          : "border-black/10 bg-white text-[#5f5f5b] hover:bg-[#f8f8f6]",
      )}
    >
      {!compact ? <span>Tryb demo</span> : null}
      <span
        className={cn(
          "relative inline-flex h-6 w-11 items-center rounded-full border border-black/10 transition",
          enabled ? "bg-[#1d1d1b]" : "bg-[#e8e8e4]",
        )}
      >
        <span
          className={cn(
            "absolute left-0.5 h-5 w-5 rounded-full bg-white shadow-sm transition-transform",
            enabled ? "translate-x-5" : "translate-x-0",
          )}
        />
      </span>
      <span className="min-w-7 text-left">{enabled ? "ON" : "OFF"}</span>
    </button>
  );
}

export const DEMO_SEARCH = {
  query: DEMO_QUERY,
  lat: Number(DEMO_LAT),
  lng: Number(DEMO_LNG),
  radiusM: Number(DEMO_RADIUS_M),
};

export function readPersistedDemoMode() {
  if (typeof window === "undefined") {
    return false;
  }
  return window.localStorage.getItem(DEMO_MODE_STORAGE_KEY) === "true";
}

export function writePersistedDemoMode(enabled: boolean) {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(DEMO_MODE_STORAGE_KEY, String(enabled));
}
