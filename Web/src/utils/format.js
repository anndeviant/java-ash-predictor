const toFixedNumber = (value, digits = 2) => {
  const numeric = Number(value);
  if (Number.isNaN(numeric)) {
    return "-";
  }
  return numeric.toFixed(digits);
};

const compactNumber = (value, digits = 2) => {
  const numeric = Number(value);
  if (Number.isNaN(numeric)) {
    return "-";
  }
  return new Intl.NumberFormat("id-ID", {
    maximumFractionDigits: digits,
    minimumFractionDigits: 0
  }).format(numeric);
};

const formatUtils = {
  toFixedNumber,
  compactNumber
};

export default formatUtils;
