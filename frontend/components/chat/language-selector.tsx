"use client";

import { Select } from "@/components/ui/select";
import { languages, type SupportedLanguage } from "@/lib/languages";

type LanguageSelectorProps = {
  value: SupportedLanguage;
  onChange: (value: SupportedLanguage) => void;
  compact?: boolean;
};

export function LanguageSelector({
  value,
  onChange,
  compact = false,
}: LanguageSelectorProps) {
  return (
    <Select
      label="Language"
      value={value}
      onChange={(next) => onChange(next as SupportedLanguage)}
      options={languages}
      className={compact ? "w-36" : "w-full"}
    />
  );
}
