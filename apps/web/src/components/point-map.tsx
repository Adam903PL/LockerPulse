"use client";

import { useEffect } from "react";
import L from "leaflet";
import { MapContainer, Marker, Popup, TileLayer, useMap } from "react-leaflet";
import { formatDistance, shortAddress } from "@/lib/point-display";
import type { PointSummary } from "@/types/points";
import { ScoreBadge } from "./score-badge";

export function PointMap({
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
    <div className="h-full min-h-[360px] overflow-hidden rounded-xl border border-black/10 bg-white shadow-sm">
      <MapContainer center={center} zoom={14} scrollWheelZoom className="h-full min-h-[360px]">
        <MapRecenter center={center} selectedPoint={selectedPoint} />
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {points.map((point) => (
          <Marker
            key={point.id}
            position={[point.coordinates.lat, point.coordinates.lng]}
            icon={markerIcon(point, selectedPoint?.id === point.id)}
            eventHandlers={{
              click: () => onSelectPoint(point),
            }}
          >
            <Popup>
              <div className="min-w-44">
                <div className="mb-2 flex items-center gap-2">
                  <ScoreBadge score={point.score} grade={point.grade} compact />
                  <div>
                    <p className="font-bold text-[#1d1d1b]">{point.name}</p>
                    <p className="text-xs text-[#5f5f5b]">{shortAddress(point)}</p>
                  </div>
                </div>
                <p className="text-xs font-semibold text-[#5f5f5b]">
                  {formatDistance(point.distance_m)} od adresu
                </p>
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
}

function MapRecenter({
  center,
  selectedPoint,
}: {
  center: [number, number];
  selectedPoint: PointSummary | null;
}) {
  const map = useMap();

  useEffect(() => {
    if (selectedPoint) {
      map.flyTo([selectedPoint.coordinates.lat, selectedPoint.coordinates.lng], 15, {
        duration: 0.8,
      });
      return;
    }
    map.flyTo(center, 14, { duration: 0.8 });
  }, [center, map, selectedPoint]);

  return null;
}

function markerIcon(point: PointSummary, selected: boolean) {
  const color = markerColor(point.grade);
  const size = selected ? 34 : 26;
  return L.divIcon({
    className: "",
    html: `<div class="locker-marker ${selected ? "locker-marker-selected" : ""}" style="--marker-color:${color};width:${size}px;height:${size}px">${point.score}</div>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

function markerColor(grade: string) {
  if (grade === "excellent") return "#ffd200";
  if (grade === "good") return "#ffe16a";
  if (grade === "fair") return "#d97706";
  if (grade === "weak") return "#ea580c";
  return "#dc2626";
}
