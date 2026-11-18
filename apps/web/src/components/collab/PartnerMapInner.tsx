"use client";

import "leaflet/dist/leaflet.css";

import { CircleMarker, MapContainer, TileLayer, Tooltip } from "react-leaflet";

import { fmt } from "@/lib/format";
import type { StatsData } from "@/lib/types";

const UIUC: [number, number] = [40.11059, -88.20727];

export default function PartnerMapInner({ partners }: { partners: StatsData["partner_map"] }) {
  const max = Math.max(...partners.map((p) => p.count), 1);
  return (
    <MapContainer bounds={[UIUC, ...partners.map((p) => [p.lat, p.lon] as [number, number])]} boundsOptions={{ padding: [28, 28] }}
                  minZoom={1} worldCopyJump scrollWheelZoom={false}
                  className="h-full w-full rounded-2xl" attributionControl>
      <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                 attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' />
      {partners.map((p) => (
        <CircleMarker key={p.id} center={[p.lat, p.lon]} radius={4 + 14 * Math.sqrt(p.count / max)}
                      pathOptions={{ color: "#13294B", weight: 1, fillColor: "#1E3A6B", fillOpacity: 0.55 }}>
          <Tooltip>{p.name}{p.city ? `, ${p.city}` : ""}: {fmt(p.count)} co-authored works</Tooltip>
        </CircleMarker>
      ))}
      <CircleMarker center={UIUC} radius={9} pathOptions={{ color: "#13294B", weight: 2, fillColor: "#FF5F05", fillOpacity: 1 }}>
        <Tooltip permanent direction="right">UIUC</Tooltip>
      </CircleMarker>
    </MapContainer>
  );
}
