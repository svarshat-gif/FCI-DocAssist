import { forwardRef, type TextareaHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export const Textarea = forwardRef<
  HTMLTextAreaElement,
  TextareaHTMLAttributes<HTMLTextAreaElement>
>(({ className, ...props }, ref) => (
  <textarea
    ref={ref}
    className={cn(
      "min-h-24 w-full resize-none rounded-lg border border-fci-line bg-white px-4 py-3 text-sm text-fci-ink outline-none transition placeholder:text-fci-steel/60 focus:border-fci-primary focus:ring-4 focus:ring-fci-primary/10 dark:border-white/10 dark:bg-white/10 dark:text-white",
      className,
    )}
    {...props}
  />
));

Textarea.displayName = "Textarea";
