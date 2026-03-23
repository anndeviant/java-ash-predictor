const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

const fetchBackendMeta = async () => {
  const response = await fetch(`${API_BASE_URL}/meta`);
  if (!response.ok) {
    throw new Error(`Gagal mengambil metadata backend (${response.status})`);
  }
  return response.json();
};

const requestPrediction = async (payload) => {
  const response = await fetch(`${API_BASE_URL}/predict`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    const safeError = await safeParseError(response);
    throw new Error(safeError);
  }

  return response.json();
};

const getApiBaseUrl = () => API_BASE_URL;

const safeParseError = async (response) => {
  try {
    const errorBody = await response.json();
    if (typeof errorBody?.detail === "string" && errorBody.detail.trim()) {
      return errorBody.detail;
    }
  } catch {
    // Use default fallback message below.
  }

  return `Request gagal (${response.status})`;
};

const apiClient = {
  fetchBackendMeta,
  requestPrediction,
  getApiBaseUrl
};

export default apiClient;
