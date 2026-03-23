import formatUtils from "../utils/format";

const ModelMetrics = ({ modelMeta }) => {
  const comparisonRows = Array.isArray(modelMeta?.comparison) ? modelMeta.comparison : [];
  const holdoutRows = Array.isArray(modelMeta?.holdout_metrics) ? modelMeta.holdout_metrics : [];

  return (
    <section className="w-full max-w-full rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:rounded-3xl sm:p-6">
      <h2 className="text-lg font-bold text-slate-900 sm:text-xl">Ringkasan Metrik Model</h2>

      <div className="mt-4 grid gap-2 sm:hidden">
        {comparisonRows.map((row) => (
          <div key={row.model} className="rounded-xl border border-slate-200 px-3 py-2.5">
            <p className="text-sm font-bold text-slate-900">{row.model}</p>
            <div className="mt-1 grid grid-cols-2 gap-x-3 gap-y-1 text-xs text-slate-700">
              <span>CV R2</span>
              <span className="text-right">{formatUtils.toFixedNumber(row.cv_r2_mean, 4)}</span>
              <span>CV MAE</span>
              <span className="text-right">{formatUtils.compactNumber(row.cv_mae_mean, 3)}</span>
              <span>CV RMSE</span>
              <span className="text-right">{formatUtils.compactNumber(row.cv_rmse_mean, 3)}</span>
              <span>Holdout R2</span>
              <span className="text-right">{formatUtils.toFixedNumber(row.holdout_r2, 4)}</span>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-4 hidden overflow-x-auto rounded-xl border border-slate-200 sm:block">
        <table className="w-full min-w-[680px] text-xs sm:text-sm">
          <thead className="bg-slate-100 text-left text-slate-700">
            <tr>
              <th className="px-3 py-2.5 font-semibold sm:px-4 sm:py-3">Model</th>
              <th className="px-3 py-2.5 font-semibold sm:px-4 sm:py-3">CV R2 Mean</th>
              <th className="px-3 py-2.5 font-semibold sm:px-4 sm:py-3">CV MAE Mean</th>
              <th className="px-3 py-2.5 font-semibold sm:px-4 sm:py-3">CV RMSE Mean</th>
              <th className="px-3 py-2.5 font-semibold sm:px-4 sm:py-3">Holdout R2</th>
            </tr>
          </thead>
          <tbody>
            {comparisonRows.map((row) => (
              <tr key={row.model} className="border-t border-slate-200">
                <td className="px-3 py-2.5 font-medium text-slate-800 sm:px-4 sm:py-3">{row.model}</td>
                <td className="px-3 py-2.5 text-slate-700 sm:px-4 sm:py-3">{formatUtils.toFixedNumber(row.cv_r2_mean, 4)}</td>
                <td className="px-3 py-2.5 text-slate-700 sm:px-4 sm:py-3">{formatUtils.compactNumber(row.cv_mae_mean, 3)}</td>
                <td className="px-3 py-2.5 text-slate-700 sm:px-4 sm:py-3">{formatUtils.compactNumber(row.cv_rmse_mean, 3)}</td>
                <td className="px-3 py-2.5 text-slate-700 sm:px-4 sm:py-3">{formatUtils.toFixedNumber(row.holdout_r2, 4)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-4 grid gap-2 sm:hidden">
        {holdoutRows.map((row) => (
          <div key={row.target} className="rounded-xl border border-slate-200 px-3 py-2.5">
            <p className="text-sm font-bold text-slate-900">{row.target}</p>
            <div className="mt-1 grid grid-cols-2 gap-x-3 gap-y-1 text-xs text-slate-700">
              <span>MAE</span>
              <span className="text-right">{formatUtils.compactNumber(row.mae, 3)}</span>
              <span>RMSE</span>
              <span className="text-right">{formatUtils.compactNumber(row.rmse, 3)}</span>
              <span>R2</span>
              <span className="text-right">{formatUtils.toFixedNumber(row.r2, 4)}</span>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-4 hidden overflow-x-auto rounded-xl border border-slate-200 sm:block">
        <table className="w-full min-w-[520px] text-xs sm:text-sm">
          <thead className="bg-slate-100 text-left text-slate-700">
            <tr>
              <th className="px-3 py-2.5 font-semibold sm:px-4 sm:py-3">Target</th>
              <th className="px-3 py-2.5 font-semibold sm:px-4 sm:py-3">MAE</th>
              <th className="px-3 py-2.5 font-semibold sm:px-4 sm:py-3">RMSE</th>
              <th className="px-3 py-2.5 font-semibold sm:px-4 sm:py-3">R2</th>
            </tr>
          </thead>
          <tbody>
            {holdoutRows.map((row) => (
              <tr key={row.target} className="border-t border-slate-200">
                <td className="px-3 py-2.5 font-medium text-slate-800 sm:px-4 sm:py-3">{row.target}</td>
                <td className="px-3 py-2.5 text-slate-700 sm:px-4 sm:py-3">{formatUtils.compactNumber(row.mae, 3)}</td>
                <td className="px-3 py-2.5 text-slate-700 sm:px-4 sm:py-3">{formatUtils.compactNumber(row.rmse, 3)}</td>
                <td className="px-3 py-2.5 text-slate-700 sm:px-4 sm:py-3">{formatUtils.toFixedNumber(row.r2, 4)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
};

export default ModelMetrics;
