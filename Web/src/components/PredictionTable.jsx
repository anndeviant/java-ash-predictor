import formatUtils from "../utils/format";

const PredictionTable = ({ prediction, weatherObservation }) => {
  if (!prediction) {
    return (
      <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:rounded-3xl sm:p-6">
        <h2 className="text-lg font-bold text-slate-900 sm:text-xl">Hasil Prediksi</h2>
        <p className="mt-3 text-sm text-slate-600">Belum ada hasil. Jalankan prediksi dari form.</p>
      </section>
    );
  }

  const rows = [
    { label: "Jarak (km)", value: prediction.jarak_km },
    { label: "Luas (km2)", value: prediction.luas_km2 },
    { label: "Sudut (deg)", value: prediction.sudut_deg },
    { label: "Radius (km)", value: prediction.radius_km }
  ];

  return (
    <section className="w-full max-w-full rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:rounded-3xl sm:p-6">
      <h2 className="text-lg font-bold text-slate-900 sm:text-xl">Hasil Prediksi</h2>

      <div className="mt-4 grid gap-2 sm:hidden">
        {rows.map((row) => (
          <div key={row.label} className="rounded-xl border border-slate-200 px-3 py-2.5">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">{row.label}</p>
            <p className="mt-1 text-sm font-bold text-slate-900">{formatUtils.compactNumber(row.value, 3)}</p>
          </div>
        ))}
      </div>

      <div className="mt-4 hidden overflow-hidden rounded-xl border border-slate-200 sm:block">
        <table className="w-full text-sm">
          <thead className="bg-slate-100 text-left text-slate-700">
            <tr>
              <th className="px-4 py-3 font-semibold">Target</th>
              <th className="px-4 py-3 font-semibold">Nilai</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.label} className="border-t border-slate-200">
                <td className="px-4 py-3 font-medium text-slate-700">{row.label}</td>
                <td className="px-4 py-3 font-semibold text-slate-900">{formatUtils.compactNumber(row.value, 3)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {weatherObservation ? (
        <div className="mt-4 rounded-xl border border-sky-200 bg-sky-50 px-3 py-3 text-xs text-sky-900 sm:px-4 sm:text-sm">
          <p className="font-semibold">Sumber data angin otomatis</p>
          <p className="mt-1">Provider: {weatherObservation.source || "open-meteo"}</p>
          <p>Zona waktu user: {weatherObservation.user_timezone || "UTC"}</p>
          <p>Waktu input user (lokal): {weatherObservation.requested_time_local || "-"}</p>
          <p>Waktu input terkonversi (UTC): {weatherObservation.requested_time_utc || "-"}</p>
          <p>Waktu observasi (UTC): {weatherObservation.observed_time || "-"}</p>
          <p>
            Kecepatan angin: {formatUtils.compactNumber(weatherObservation.wind_speed_km_h, 2)} km/jam
          </p>
          <p>
            Arah angin: {formatUtils.compactNumber(weatherObservation.wind_direction_deg, 2)} derajat
          </p>
        </div>
      ) : null}
    </section>
  );
};

export default PredictionTable;
