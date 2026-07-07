import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

type SelectProps = {
  value: string;
  onChange: (value: string) => void;
  options: readonly string[];
  label: string;
  className?: string;
};

export function Select({ value, onChange, options, label, className }: SelectProps) {
  return (
    <label className={cn("relative block", className)}>
      <span className="sr-only">{label}</span>
      <select
        aria-label={label}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="h-10 w-full appearance-none rounded-lg border border-fci-line bg-white pl-3 pr-9 text-sm font-medium text-fci-ink outline-none transition focus:border-fci-primary focus:ring-4 focus:ring-fci-primary/10 dark:border-white/10 dark:bg-white/10 dark:text-white"
      >
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
      <ChevronDown
        aria-hidden="true"
        className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-fci-steel"
      />
    </label>
  );
}
