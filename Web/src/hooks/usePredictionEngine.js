import { useCallback, useEffect, useState } from "react";
import apiClient from "../services/apiClient";

const usePredictionEngine = (defaultVolcano) => {
  const [validation, setValidation] = useState({
    isValid: false,
    expectedModelName: "xgboost",
    actualModelName: "unknown",
    message: "Memeriksa validitas model backend"
  });
  const [modelMeta, setModelMeta] = useState(null);

  const [prediction, setPrediction] = useState(null);
  const [impactData, setImpactData] = useState(null);
  const [weatherObservation, setWeatherObservation] = useState(null);
  const [selectedVolcano, setSelectedVolcano] = useState(defaultVolcano);
  const [errorMessage, setErrorMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const syncBackendMeta = useCallback(async () => {
    setIsLoading(true);

    try {
      const meta = await apiClient.fetchBackendMeta();
      const actualModelName = String(meta?.model_name || "unknown").toLowerCase();
      const isValid = actualModelName === "xgboost";

      setModelMeta(meta);
      setValidation({
        isValid,
        expectedModelName: "xgboost",
        actualModelName,
        message: isValid
          ? "Model final valid: xgboost"
          : "Model final tidak valid, harus xgboost"
      });

      if (!isValid) {
        setErrorMessage("Prediksi diblokir karena model backend bukan xgboost");
      } else {
        setErrorMessage("");
      }
    } catch (error) {
      setValidation({
        isValid: false,
        expectedModelName: "xgboost",
        actualModelName: "unreachable",
        message: "Backend tidak tersedia"
      });
      setErrorMessage("Backend API tidak dapat diakses");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    syncBackendMeta();
  }, [syncBackendMeta]);

  const runPrediction = async (formValues, volcano) => {
    if (!validation.isValid) {
      setErrorMessage(validation.message);
      setPrediction(null);
      setImpactData(null);
      setWeatherObservation(null);
      return;
    }

    setIsLoading(true);

    try {
      const userTimeZone = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
      const localEventDate = new Date(
        Number(formValues.year),
        Number(formValues.month) - 1,
        Number(formValues.day),
        Number(formValues.hour),
        0,
        0
      );
      const timezoneOffsetMinutes = Number.isNaN(localEventDate.getTime())
        ? -new Date().getTimezoneOffset()
        : -localEventDate.getTimezoneOffset();

      const payload = {
        volcano_name: volcano.name,
        tinggi_letusan_m: Number(formValues.tinggi_letusan_m),
        amplitudo: Number(formValues.amplitudo),
        duration: Number(formValues.duration),
        alert_level: String(formValues.alert_level),
        year: Number(formValues.year),
        month: Number(formValues.month),
        day: Number(formValues.day),
        hour: Number(formValues.hour),
        timezone_name: userTimeZone,
        timezone_offset_minutes: timezoneOffsetMinutes
      };

      const response = await apiClient.requestPrediction(payload);
      const result = response?.prediction || null;
      const impact = response?.impact || null;
      const weather = response?.weather_observation || null;

      setPrediction(result);
      setImpactData(impact);
      setWeatherObservation(weather);
      setSelectedVolcano(volcano);
      setErrorMessage("");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Prediksi gagal diproses");
      setPrediction(null);
      setImpactData(null);
      setWeatherObservation(null);
    } finally {
      setIsLoading(false);
    }
  };

  return {
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
  };
};

export default usePredictionEngine;
