import { ReactNode } from "react";

import { Panel } from "@/components/ui";

export function PageFrame({
  eyebrow,
  title,
  description,
  children
}: {
  eyebrow: string;
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <Panel className="overflow-visible">
      <div className="mb-8 max-w-3xl">
        <p className="eyebrow">{eyebrow}</p>
        <h2 className="mt-3 text-3xl font-semibold tracking-tight text-white md:text-4xl">{title}</h2>
        <p className="mt-3 max-w-2xl text-sm leading-7 text-muted">{description}</p>
      </div>
      <div>{children}</div>
    </Panel>
  );
}
