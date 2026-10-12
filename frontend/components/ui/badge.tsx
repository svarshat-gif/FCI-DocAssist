import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export function Badge({ className, ...props }: HTMLAttributes<HTMLSpanElement>) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-md border border-fci-primary/15 bg-fci-light px-2.5 py-1 text-xs font-medium text-fci-dark dark:border-fci-primary/30 dark:bg-fci-primary/15 dark:text-fci-light",
        className,
      )}
      {...props}
    />
  );
}
