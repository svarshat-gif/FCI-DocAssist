export const languages = [
  "English",
  "Hindi",
  "Kannada",
  "Telugu",
  "Tamil",
  "Malayalam",
  "Marathi",
  "Gujarati",
  "Bengali",
  "Punjabi",
] as const;

export type SupportedLanguage = (typeof languages)[number];
