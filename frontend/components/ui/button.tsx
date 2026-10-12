import { forwardRef, type ButtonHTMLAttributes } from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex h-10 items-center justify-center gap-2 rounded-lg px-4 text-sm font-medium transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-fci-primary disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        primary: "bg-fci-primary text-white shadow-crisp hover:bg-fci-dark",
        secondary:
          "border border-fci-line bg-white text-fci-ink hover:border-fci-primary/30 hover:bg-fci-light dark:border-white/10 dark:bg-white/10 dark:text-white dark:hover:bg-white/10",
        ghost:
          "text-fci-steel hover:bg-fci-light hover:text-fci-dark dark:text-white/75 dark:hover:bg-white/10 dark:hover:text-white",
        danger: "bg-red-600 text-white hover:bg-red-700",
      },
      size: {
        sm: "h-9 px-3",
        md: "h-10 px-4",
        icon: "h-10 w-10 px-0",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "md",
    },
  },
);

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> &
  VariantProps<typeof buttonVariants>;

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, title, ...props }, ref) => (
    <button
      ref={ref}
      title={title || (size === "icon" ? props["aria-label"] : undefined)}
      className={cn(buttonVariants({ variant, size }), className)}
      {...props}
    />
  ),
);

Button.displayName = "Button";
