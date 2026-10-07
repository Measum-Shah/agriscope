/**
 * Single source of truth for physical validation ranges and auth constraints.
 * As defined in PROJECT_CONTEXT section E:
 * - temperature -10..50 °C
 * - humidity 0..100 %
 * - wind 0..30 m/s
 * - solar radiation 0..35 MJ/m²/day
 */
export const VALIDATION_RANGES = {
  temperature: {
    min: -10,
    max: 50,
    unit: '°C',
    label: 'Temperature',
  },
  humidity: {
    min: 0,
    max: 100,
    unit: '%',
    label: 'Relative Humidity',
  },
  windSpeed: {
    min: 0,
    max: 30,
    unit: 'm/s',
    label: 'Wind Speed',
  },
  solarRadiation: {
    min: 0,
    max: 35,
    unit: 'MJ/m²/day',
    label: 'Solar Radiation',
  },
} as const;

export const ET_CLASSIFICATION = {
  LOW: { threshold: 2.0, label: 'Low (< 2 mm/day)' },
  MODERATE: { min: 2.0, max: 5.0, label: 'Moderate (2–5 mm/day)' },
  HIGH: { threshold: 5.0, label: 'High (> 5 mm/day)' },
} as const;

export const AUTH_RULES = {
  password: {
    minLength: 8,
    requireUppercase: true,
    requireDigit: true,
    regex: /^(?=.*[A-Z])(?=.*\d).{8,}$/,
    errorMessage:
      'Password must be at least 8 characters long and contain at least one uppercase letter and one digit.',
  },
  name: {
    minLength: 2,
    maxLength: 100,
  },
  totpCode: {
    length: 6,
    regex: /^\d{6}$/,
  },
} as const;
