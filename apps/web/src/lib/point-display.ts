import type { PointSummary } from "@/types/points";

export function formatDistance(distanceM: number | null) {
  if (distanceM == null) {
    return "brak danych";
  }
  if (distanceM < 1000) {
    return `${distanceM} m`;
  }
  return `${(distanceM / 1000).toFixed(1)} km`;
}

export function scoreLabel(grade: string) {
  if (grade === "excellent") {
    return "Polecany";
  }
  if (grade === "good") {
    return "Dobry";
  }
  if (grade === "fair") {
    return "W porządku";
  }
  if (grade === "weak") {
    return "Słaby";
  }
  return "Krytyczny";
}

export function statusLabel(status: string | null) {
  if (status === "Operating") {
    return "Działa";
  }
  if (status === "Disabled") {
    return "Niedostępny";
  }
  if (status === "Created") {
    return "W przygotowaniu";
  }
  return "Nieznany";
}

export function statusClass(status: string | null) {
  if (status === "Operating") {
    return "border-emerald-200 bg-emerald-50 text-emerald-800";
  }
  if (status === "Disabled") {
    return "border-red-200 bg-red-50 text-red-800";
  }
  if (status === "Created") {
    return "border-amber-200 bg-amber-50 text-amber-900";
  }
  return "border-zinc-200 bg-zinc-100 text-zinc-700";
}

export function riskClass(level: string | null | undefined) {
  if (level === "ok") {
    return "border-emerald-200 bg-emerald-50 text-emerald-800";
  }
  if (level === "watch") {
    return "border-[#ffd200] bg-[#fff4b8] text-[#1d1d1b]";
  }
  if (level === "risky") {
    return "border-orange-200 bg-orange-50 text-orange-800";
  }
  if (level === "critical") {
    return "border-red-200 bg-red-50 text-red-800";
  }
  return "border-zinc-200 bg-zinc-100 text-zinc-700";
}

export function riskLabel(level: string | null | undefined) {
  if (level === "ok") {
    return "Stabilny";
  }
  if (level === "watch") {
    return "Uwaga";
  }
  if (level === "risky") {
    return "Ryzyko";
  }
  if (level === "critical") {
    return "Krytyczny";
  }
  return "Nieznany";
}

export function shortAddress(point: PointSummary) {
  if (!point.address) {
    return "Adres niedostępny";
  }
  const [firstLine] = point.address.split(",");
  return firstLine?.trim() || point.address;
}

export function formatFunctionName(value: string) {
  const dictionary: Record<string, string> = {
    allegro_courier_collect: "Allegro kurier: odbiór",
    allegro_courier_reverse_return_send: "Allegro kurier: zwrot",
    allegro_courier_send: "Allegro kurier: nadanie",
    allegro_letter_reverse_return_send: "Allegro list: zwrot",
    allegro_letter_send: "Allegro list: nadanie",
    allegro_parcel_collect: "Allegro: odbiór paczki",
    allegro_parcel_reverse_return_send: "Allegro: zwrot paczki",
    allegro_parcel_send: "Allegro: nadanie paczki",
    cross_network_parcel_collect: "odbiór z innej sieci",
    cross_network_parcel_send: "nadanie do innej sieci",
    parcel: "obsługa paczek",
    parcel_collect: "odbiór paczki",
    parcel_send: "nadanie paczki",
    parcel_reverse_return_send: "zwrot",
    standard_courier_send: "nadanie kurierem",
    standard_courier_reverse_return_send: "kurier: zwrot",
    air_sensor: "czujnik powietrza",
  };

  return dictionary[value] ?? value.replaceAll("_", " ");
}

export function pointHref(point: PointSummary, returnParams: URLSearchParams) {
  const suffix = returnParams.toString();
  return `/points/${point.country}/${point.name}${suffix ? `?${suffix}` : ""}`;
}
