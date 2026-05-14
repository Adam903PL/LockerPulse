"use client";

import dynamic from "next/dynamic";
import type { PointSummary } from "@/types/points";

const PointMap = dynamic(() => import("./point-map").then((mod) => mod.PointMap), {
  ssr: false,
  loading: () => (
    <div className="flex h-full min-h-[360px] items-center justify-center rounded-xl border border-black/10 bg-white text-sm font-semibold text-[#5f5f5b]">
      Ładuję mapę
    </div>
  ),
});

export function MapShell({
  points,
  selectedPoint,
  center,
  onSelectPoint,
}: {
  points: PointSummary[];
  selectedPoint: PointSummary | null;
  center: [number, number];
  onSelectPoint: (point: PointSummary) => void;
}) {
  return (
    <PointMap
      points={points}
      selectedPoint={selectedPoint}
      center={center}
      onSelectPoint={onSelectPoint}
    />
  );
}
