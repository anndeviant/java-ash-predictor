import { useEffect, useMemo, useState } from "react";

const PredictionForm = ({
  volcanoes,
  alertLevels,
  defaults,
  onPredict,
  canPredict,
  isLoading
}) => {
  const [formValues, setFormValues] = useState(defaults);

  const selectedVolcano = useMemo(
    () => volcanoes.find((item) => item.name === formValues.volcano_filter) || volcanoes[0],
    [volcanoes, formValues.volcano_filter]
  );

  const updateValue = (key, value) => {
    setFormValues((previous) => ({ ...previous, [key]: value }));
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    onPredict(formValues, selectedVolcano);
  };

  const getTimeNow = () => {
    const now = new Date();
    return {
      year: now.getFullYear(),
      month: now.getMonth() + 1,
      day: now.getDate(),
      hour: now.getHours()
    };
  };

  useEffect(() => {
    const currentTime = getTimeNow();
    setFormValues((previous) => ({ ...previous, ...currentTime }));
  }, []);

  return (
    <section className="w-full max-w-full rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:rounded-3xl sm:p-6">
      <h2 className="text-lg font-bold text-slate-900 sm:text-xl">Input Prediksi Manual</h2>

      <form onSubmit={handleSubmit} className="mt-4 grid grid-cols-1 gap-3 sm:mt-5 sm:gap-4 md:grid-cols-2">
        <label className="flex flex-col gap-1.5 md:col-span-2">
          <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-600">Pilih Gunung</span>
          <select
            className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
            value={formValues.volcano_filter}
            onChange={(event) => updateValue("volcano_filter", event.target.value)}
          >
            {volcanoes.map((volcano) => (
              <option key={volcano.name} value={volcano.name}>
                {volcano.name}
              </option>
            ))}
          </select>
        </label>

        <ReadOnlyField label="Latitude" value={selectedVolcano.latitude} />
        <ReadOnlyField label="Longitude" value={selectedVolcano.longitude} />
        <ReadOnlyField label="Elevation" value={selectedVolcano.elevation} />

        <InputField
          label="Tinggi Letusan (m)"
          type="number"
          value={formValues.tinggi_letusan_m}
          onChange={(value) => updateValue("tinggi_letusan_m", Number(value))}
        />
        <InputField
          label="Amplitudo"
          type="number"
          value={formValues.amplitudo}
          onChange={(value) => updateValue("amplitudo", Number(value))}
          step="0.1"
        />
        <InputField
          label="Durasi"
          type="number"
          value={formValues.duration}
          onChange={(value) => updateValue("duration", Number(value))}
        />

        <label className="flex flex-col gap-1.5">
          <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-600">Alert Level</span>
          <select
            className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200"
            value={formValues.alert_level}
            onChange={(event) => updateValue("alert_level", event.target.value)}
          >
            {alertLevels.map((level) => (
              <option key={level} value={level}>
                {level}
              </option>
            ))}
          </select>
        </label>

        <InputField
          label="Tahun"
          type="number"
          value={formValues.year}
          onChange={(value) => updateValue("year", Number(value))}
        />
        <InputField
          label="Bulan"
          type="number"
          value={formValues.month}
          onChange={(value) => updateValue("month", Number(value))}
        />
        <InputField
          label="Tanggal"
          type="number"
          value={formValues.day}
          onChange={(value) => updateValue("day", Number(value))}
        />
        <InputField
          label="Jam"
          type="number"
          value={formValues.hour}
          onChange={(value) => updateValue("hour", Number(value))}
        />

        <button
          type="submit"
          disabled={!canPredict}
          className="md:col-span-2 rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400 sm:py-3"
        >
          {isLoading ? "Memproses Prediksi" : "Jalankan Prediksi"}
        </button>
      </form>
    </section>
  );
};

const InputField = ({ label, value, onChange, type = "text", step }) => {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-600">{label}</span>
      <input
        className="min-h-[42px] w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-900 outline-none transition focus:border-slate-500 focus:ring-2 focus:ring-slate-200 sm:min-h-[44px]"
        type={type}
        value={value}
        step={step}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
};

const ReadOnlyField = ({ label, value }) => {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-600">{label}</span>
      <input
        className="min-h-[42px] w-full rounded-xl border border-slate-300 bg-slate-100 px-3 py-2.5 text-sm text-slate-900 outline-none sm:min-h-[44px]"
        type="text"
        value={value}
        readOnly
      />
    </label>
  );
};

export default PredictionForm;
