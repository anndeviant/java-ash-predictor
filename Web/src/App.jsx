import PageHeader from "./components/PageHeader";
import StatusBanner from "./components/StatusBanner";
import PredictionForm from "./components/PredictionForm";
import PredictionTable from "./components/PredictionTable";
import ImpactSummaryTable from "./components/ImpactSummaryTable";
import ModelMetrics from "./components/ModelMetrics";
import AshDispersionMap from "./components/AshDispersionMap";
import volcanoes from "./data/volcanoes.json";
import alertLevels from "./data/alertLevels.json";
import featureDefaults from "./data/featureDefaults.json";
import staticModelMeta from "./data/modelMeta.json";
import usePredictionEngine from "./hooks/usePredictionEngine";
import apiClient from "./services/apiClient";

const buildInitialFormDefaults = () => ({
  volcano_filter: volcanoes[0]?.name || "Merapi",
  ...featureDefaults
});

const App = () => {
  const initialDefaults = buildInitialFormDefaults();

  const {
    validation,
    modelMeta,
    prediction,
    impactData,
    weatherObservation,
    selectedVolcano,
    errorMessage,
    isLoading,
    syncBackendMeta,
    runPrediction
  } = usePredictionEngine(volcanoes[0]);

  const metricsMeta = modelMeta ?? staticModelMeta;
  const volcanoOptions = modelMeta?.volcanoes ?? volcanoes;
  const alertOptions = modelMeta?.alert_levels ?? alertLevels;

  return (
    <div className="relative min-h-screen overflow-x-hidden bg-slate-50 px-3 py-5 text-slate-900 sm:px-4 sm:py-6 md:px-8 md:py-8">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_10%_20%,rgba(251,191,36,0.18),transparent_28%),radial-gradient(circle_at_85%_12%,rgba(56,189,248,0.2),transparent_32%),radial-gradient(circle_at_50%_90%,rgba(148,163,184,0.16),transparent_25%)]" />

      <main className="relative mx-auto flex w-full max-w-7xl flex-col gap-4 sm:gap-5 md:gap-6">
        <PageHeader />

        <StatusBanner validation={validation} />

        <div className="rounded-2xl border border-slate-200 bg-white px-3 py-3 text-[11px] text-slate-600 sm:px-4 sm:text-xs">
          <p className="break-all sm:break-normal">
            Backend API: {apiClient.getApiBaseUrl()} | Status: {isLoading ? "memuat" : "siap"}
          </p>
          <button
            type="button"
            onClick={syncBackendMeta}
            className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-100 sm:w-auto sm:text-sm"
          >
            Sinkronisasi Metadata
          </button>
        </div>

        {errorMessage ? (
          <div className="rounded-2xl border border-rose-200 bg-rose-50 px-3 py-3 text-sm text-rose-800 sm:px-4">
            {errorMessage}
          </div>
        ) : null}

        <div className="rounded-2xl border border-amber-200 bg-amber-50 px-3 py-3 text-sm leading-relaxed text-amber-900 sm:px-4">
          Prediksi menggunakan model backend (XGBoost). Visual peta menampilkan interpretasi sektor dampak berbasis output model,
          namun hanya untuk sebaran abu yang ada dalam 2 jam kedepan setelah erupsi.
        </div>

        <section className="grid gap-6 xl:grid-cols-[1.2fr_1fr]">
          <PredictionForm
            volcanoes={volcanoOptions}
            alertLevels={alertOptions}
            defaults={initialDefaults}
            onPredict={runPrediction}
            canPredict={validation.isValid && !isLoading}
            isLoading={isLoading}
          />

          <div className="grid gap-6">
            <PredictionTable prediction={prediction} weatherObservation={weatherObservation} />
            <ModelMetrics modelMeta={metricsMeta} />
          </div>
        </section>

        <AshDispersionMap impactData={impactData} volcano={selectedVolcano} />
        <ImpactSummaryTable impactData={impactData} />
      </main>
    </div>
  );
};

export default App;