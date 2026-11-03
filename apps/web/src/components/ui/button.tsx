import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "../../lib/utils";

// Local shadcn-style primitive: semantic button, optional Slot, composable variants.
const variants = cva("button", {
  variants: {
    variant: {
      default: "button-primary",
      outline: "button-outline",
      ghost: "button-ghost",
    },
  },
  defaultVariants: { variant: "default" },
});
type Props = React.ComponentProps<"button"> &
  VariantProps<typeof variants> & { asChild?: boolean };
export function Button({
  className,
  variant,
  asChild = false,
  ...props
}: Props) {
  const Component = asChild ? Slot : "button";
  return (
    <Component className={cn(variants({ variant, className }))} {...props} />
  );
}
