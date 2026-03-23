import { useEffect, useMemo, useState } from "react";
import DeckGL from "@deck.gl/react";
import { PathLayer, PolygonLayer, ScatterplotLayer } from "@deck.gl/layers";
import { Map } from "react-map-gl/maplibre";
import constants from "../utils/constants";

const withStableAlpha = (color) => {
  if (!Array.isArray(color) || color.length < 3) {
    return [100, 116, 139, 190];
  }

  const [r, g, b, a = 255] = color;
  return [r, g, b, Math.max(175, Math.min(230, a + 70))];
};

const AshDispersionMap = ({ impactData, volcano }) => {
  const [isWebGLReady, setIsWebGLReady] = useState(false);
  const [isWebGLChecked, setIsWebGLChecked] = useState(false);

  useEffect(() => {
    const canvas = document.createElement("canvas");
    const context = canvas.getContext("webgl2") || canvas.getContext("webgl");
    setIsWebGLReady(Boolean(context));
    setIsWebGLChecked(true);
  }, []);

  const polygons = impactData?.polygons ?? [];
  const centerline = impactData?.centerline ?? [];
  const points = impactData?.points ?? [];
  const maxDistance = Number(impactData?.metadata?.max_distance ?? impactData?.maxDistance ?? 1);
  const polygonBands = useMemo(
    () => [...polygons].sort((a, b) => Number(b.radius_km ?? 0) - Number(a.radius_km ?? 0)),
    [polygons]
  );

  const layers = useMemo(
    () => [
      new PolygonLayer({
        id: "ash-polygons",
        data: polygonBands,
        getPolygon: (item) => item.coordinates,
        getFillColor: (item) => withStableAlpha(item.fill_color),
        getLineColor: [30, 41, 59, 220],
        lineWidthUnits: "pixels",
        lineWidthMinPixels: 1.25,
        filled: true,
        stroked: true,
        opacity: 0.92,
        parameters: { depthTest: false },
        pickable: true
      }),
      new PathLayer({
        id: "ash-path",
        data: centerline,
        getPath: (item) => item.path,
        getColor: [178, 34, 34, 235],
        widthScale: 1,
        widthMinPixels: 2.5,
        parameters: { depthTest: false },
        pickable: false
      }),
      new ScatterplotLayer({
        id: "ash-points",
        data: points,
        getPosition: (item) => [item.lon, item.lat],
        getFillColor: (item) => item.color,
        radiusUnits: "pixels",
        getRadius: (item) => (item.name === "Pusat erupsi" ? 6 : 7),
        radiusMinPixels: 4,
        radiusMaxPixels: 10,
        stroked: true,
        getLineColor: [255, 255, 255, 210],
        lineWidthMinPixels: 1,
        parameters: { depthTest: false },
        pickable: true
      })
    ],
    [centerline, points, polygonBands]
  );

  if (!impactData || !volcano) {
    return (
      <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:rounded-3xl sm:p-6">
        <h2 className="text-lg font-bold text-slate-900 sm:text-xl">Peta Sebaran Abu</h2>
        <p className="mt-3 text-sm text-slate-600">Peta akan aktif setelah prediksi dijalankan.</p>
      </section>
    );
  }

  if (!isWebGLChecked) {
    return (
      <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:rounded-3xl sm:p-6">
        <h2 className="text-lg font-bold text-slate-900 sm:text-xl">Peta Sebaran Abu</h2>
        <p className="mt-3 text-sm text-slate-600">Memeriksa dukungan WebGL pada perangkat.</p>
      </section>
    );
  }

  if (!isWebGLReady) {
    return (
      <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:rounded-3xl sm:p-6">
        <h2 className="text-lg font-bold text-slate-900 sm:text-xl">Peta Sebaran Abu</h2>
        <div className="mt-3 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2.5 text-sm text-amber-900">
          Perangkat atau browser tidak mendukung WebGL secara penuh. Peta interaktif dinonaktifkan,
          namun hasil prediksi dan ringkasan dampak tetap tersedia.
        </div>
      </section>
    );
  }

  const zoom = Math.max(6.5, 10.7 - Math.log10(maxDistance + 1) * 1.7);

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:rounded-3xl sm:p-6">
      <h2 className="text-lg font-bold text-slate-900 sm:text-xl">Peta Sebaran Abu</h2>
      <p className="mt-2 text-sm text-slate-600">
        Visualisasi sektor arah angin berbasis output model prediksi backend.
      </p>

      <div className="relative mt-4 h-[340px] overflow-hidden rounded-2xl border border-slate-200 sm:h-[420px] lg:h-[460px]">
        <DeckGL
          className="h-full w-full"
          initialViewState={{
            longitude: volcano.longitude,
            latitude: volcano.latitude,
            zoom,
            pitch: 10,
            bearing: 0
          }}
          controller
          layers={layers}
          getTooltip={({ object }) => {
            if (!object?.label) {
              return null;
            }
            return {
              text: `Level ${object.level} - ${object.label}\nRadius: ${object.radius_km} km\nSkor: ${object.impact_score}`
            };
          }}
        >
          <Map mapStyle={constants.MAP_STYLE} />
        </DeckGL>
      </div>
    </section>
  );
};

export default AshDispersionMap;
