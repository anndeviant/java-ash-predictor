import clsx from "clsx";

const StatusBanner = ({ validation }) => {
  return (
    <div
      className={clsx(
        "rounded-2xl border px-4 py-3 text-sm",
        validation.isValid
          ? "border-emerald-200 bg-emerald-50 text-emerald-800"
          : "border-rose-200 bg-rose-50 text-rose-800"
      )}
    >
      <p className="font-semibold">Validasi Model</p>
      <p className="mt-1">
        {validation.message}. Model terdeteksi: {validation.actualModelName}.
      </p>
    </div>
  );
};

export default StatusBanner;
