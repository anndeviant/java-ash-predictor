import formatUtils from "../utils/format";

const ImpactSummaryTable = ({ impactData }) => {
  if (!impactData) {
    return (
      <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:rounded-3xl sm:p-6">
        <h2 className="text-lg font-bold text-slate-900 sm:text-xl">Ringkasan Dampak</h2>
        <p className="mt-3 text-sm text-slate-600">Data dampak akan muncul setelah prediksi dijalankan.</p>
      </section>
    );
  }

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:rounded-3xl sm:p-6">
      <h2 className="text-lg font-bold text-slate-900 sm:text-xl">Ringkasan Dampak</h2>
      <div className="mt-4 overflow-x-auto rounded-xl border border-slate-200">
        <table className="w-full min-w-[640px] text-xs sm:text-sm">
          <thead className="bg-slate-100 text-left text-slate-700">
            <tr>
              <th className="px-3 py-2.5 font-semibold sm:px-4 sm:py-3">Level</th>
              <th className="px-3 py-2.5 font-semibold sm:px-4 sm:py-3">Kategori</th>
              <th className="px-3 py-2.5 font-semibold sm:px-4 sm:py-3">Radius (km)</th>
              <th className="px-3 py-2.5 font-semibold sm:px-4 sm:py-3">Estimasi Luas (km2)</th>
              <th className="px-3 py-2.5 font-semibold sm:px-4 sm:py-3">Impact Score</th>
            </tr>
          </thead>
          <tbody>
            {impactData.summary.map((row) => (
              <tr key={row.level} className="border-t border-slate-200">
                <td className="px-3 py-2.5 font-medium text-slate-800 sm:px-4 sm:py-3">{row.level}</td>
                <td className="px-3 py-2.5 text-slate-700 sm:px-4 sm:py-3">{row.kategori}</td>
                <td className="px-3 py-2.5 text-slate-700 sm:px-4 sm:py-3">{formatUtils.compactNumber(row.radius_km, 2)}</td>
                <td className="px-3 py-2.5 text-slate-700 sm:px-4 sm:py-3">{formatUtils.compactNumber(row.estimasi_luas_km2, 2)}</td>
                <td className="px-3 py-2.5 text-slate-700 sm:px-4 sm:py-3">{formatUtils.compactNumber(row.impact_score, 3)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
};

export default ImpactSummaryTable;
