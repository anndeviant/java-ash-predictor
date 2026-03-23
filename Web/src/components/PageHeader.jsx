const PageHeader = () => {
  return (
    <header className="relative overflow-hidden rounded-2xl border border-slate-200 bg-gradient-to-r from-amber-100 via-white to-sky-100 p-4 shadow-sm sm:rounded-3xl sm:p-6">
      <div className="absolute -right-10 -top-10 h-28 w-28 rounded-full bg-amber-300/20 blur-2xl sm:-right-14 sm:-top-14 sm:h-44 sm:w-44" />
      <div className="absolute -bottom-8 left-8 h-24 w-24 rounded-full bg-sky-300/20 blur-2xl sm:-bottom-10 sm:left-12 sm:h-40 sm:w-40" />
      <div className="relative">
        <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-600 sm:text-xs sm:tracking-[0.18em]">
          Dashboard Prediksi Abu Vulkanik (2 Jam Setelah Erupsi)
        </p>
        <h1 className="mt-2 text-2xl font-extrabold leading-tight text-slate-900 sm:text-3xl md:text-4xl">
          Prediksi Multi-Output Berbasis Model XGBoost
        </h1>
        <p className="mt-3 max-w-3xl text-xs leading-relaxed text-slate-700 sm:text-sm">
          Aplikasi web ini memakai backend API Python untuk inferensi model asli.
          Hasil prediksi ditampilkan dalam bentuk tabel dan peta sektor dampak
          agar pengguna dapat membaca arah dan tingkat sebaran abu secara cepat.
          Model hanya memprediksi sebaran abu 2 jam setelah erupsi saja.
        </p>
      </div>
    </header>
  );
};

export default PageHeader;
