import * as React from "react";
import { cn } from "@/lib/utils";

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  tone?: { fg: string; bg: string; ring: string };
  dot?: boolean;
}

/** A status chip. Colour never carries meaning alone — always paired with text. */
export function Badge({ className, tone, dot = false, children, ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-2xs font-medium leading-tight",
        !tone && "border-line bg-surface-raised text-ink-muted",
        className,
      )}
      style={tone ? { color: tone.fg, backgroundColor: tone.bg, borderColor: tone.ring } : undefined}
      {...props}
    >
      {dot && tone && (
        <span aria-hidden className="size-1.5 rounded-full" style={{ backgroundColor: tone.fg }} />
      )}
      {children}
    </span>
  );
}
