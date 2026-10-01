/**
 * Reference lists for the New Check form. DISTRICTS is the backend's list (backend/app/services/districts.py): the value
 * sent to the API is the English name; the label shown is looked up in the dictionary as `district.<name>`.
 */
export const DISTRICTS = [
  "Ahilyanagar",
  "Akola",
  "Amravati",
  "Beed",
  "Bhandara",
  "Buldhana",
  "Chandrapur",
  "Chhatrapati Sambhajinagar",
  "Dharashiv",
  "Dhule",
  "Gadchiroli",
  "Gondia",
  "Hingoli",
  "Jalgaon",
  "Jalna",
  "Kolhapur",
  "Latur",
  "Mumbai City",
  "Mumbai Suburban",
  "Nagpur",
  "Nanded",
  "Nandurbar",
  "Nashik",
  "Palghar",
  "Parbhani",
  "Pune",
  "Raigad",
  "Ratnagiri",
  "Sangli",
  "Satara",
  "Sindhudurg",
  "Solapur",
  "Thane",
  "Wardha",
  "Washim",
  "Yavatmal",
] as const;
export type District = (typeof DISTRICTS)[number];
export const DEFAULT_DISTRICT: District = "Pune";

/** Soybean growth stages. The stored value is the short code (for example "R3"); the label is `growthStage.<code>`. */
export const GROWTH_STAGES = ["VE", "VC", "V1", "V2", "V3", "R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8"] as const;
export type GrowthStage = (typeof GROWTH_STAGES)[number];

/** Limits that mirror the API (CaseCreate, QuestionCreate, image upload). */
export const LIMITS = {
  textMax: 2000,
  rainfallMax: 200,
  growthStageMax: 100,
  imageMaxBytes: 10 * 1024 * 1024,
} as const;
