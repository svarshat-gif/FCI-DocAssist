import { forwardRef, type InputHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <input
      ref={ref}
      className={cn(
        "h-11 w-full rounded-lg border border-fci-line bg-white px-3 text-sm text-fci-ink outline-none transition placeholder:text-fci-steel/60 focus:border-fci-primary focus:ring-4 focus:ring-fci-primary/10 dark:border-white/10 dark:bg-white/10 dark:text-white",
        className,
      )}
      {...props}
    />
  ),
);

Input.displayName = "Input";
