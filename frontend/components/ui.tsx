import type { ReactNode } from "react";

function cn(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(" ");
}

export function Panel({
  children,
  className
}: {
  children: ReactNode;
  className?: string;
}) {
  return <div className={cn("surface", className)}>{children}</div>;
}

export function SoftPanel({
  children,
  className
}: {
  children: ReactNode;
  className?: string;
}) {
  return <div className={cn("surface-soft", className)}>{children}</div>;
}

export function Badge({
  children,
  tone = "default"
}: {
  children: ReactNode;
  tone?: "default" | "accent" | "warm" | "danger";
}) {
  const toneClass =
    tone === "accent"
      ? "badge-accent"
      : tone === "warm"
        ? "badge-warm"
        : tone === "danger"
          ? "badge-danger"
          : "";

  return <span className={cn("badge", toneClass)}>{children}</span>;
}

export function StatTile({
  label,
  value,
  detail,
  tone = "default"
}: {
  label: string;
  value: string;
  detail?: string;
  tone?: "default" | "accent" | "warm";
}) {
  return (
    <Panel className={cn("min-h-[11rem]", tone === "accent" ? "surface-accent" : "", tone === "warm" ? "surface-warm" : "")}>
      <p className="text-xs uppercase tracking-[0.24em] text-muted">{label}</p>
      <p className="mt-6 max-w-[10ch] text-3xl font-semibold tracking-tight text-white">{value}</p>
      {detail ? <p className="mt-4 text-sm leading-6 text-muted">{detail}</p> : null}
    </Panel>
  );
}

export function EmptyState({
  title,
  description
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="surface-soft flex min-h-[12rem] flex-col justify-center text-center">
      <p className="text-lg font-medium text-white">{title}</p>
      <p className="mx-auto mt-3 max-w-md text-sm leading-6 text-muted">{description}</p>
    </div>
  );
}
