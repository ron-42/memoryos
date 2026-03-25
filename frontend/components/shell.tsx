"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ReactNode } from "react";

import { Badge, SoftPanel } from "@/components/ui";

const nav = [
  { href: "/home", label: "Home" },
  { href: "/capture", label: "Capture" },
  { href: "/memories", label: "Memories" },
  { href: "/chat", label: "Chat" },
  { href: "/graph", label: "Graph" }
];

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen bg-background text-white">
      <div className="mx-auto grid min-h-screen max-w-[1440px] gap-4 px-4 py-4 lg:grid-cols-[16rem_minmax(0,1fr)] lg:px-6">
        <aside className="surface w-full lg:sticky lg:top-4 lg:flex lg:h-[calc(100vh-2rem)] lg:flex-col">
          <div>
            <Badge tone="accent">MemoryOS</Badge>
            <h1 className="mt-4 text-2xl font-semibold leading-tight text-white">Personal memory workspace</h1>
            <p className="mt-3 max-w-xs text-sm leading-6 text-muted">
              Capture, retrieve, and connect what you read.
            </p>
          </div>

          <nav className="mt-8 space-y-1.5">
            {nav.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={`nav-link ${pathname === item.href ? "nav-link-active" : ""}`}
              >
                <div className="flex items-center justify-between gap-3">
                  <span className="text-sm font-medium">{item.label}</span>
                  <span className="text-[11px] uppercase tracking-[0.14em] text-muted">
                    {item.label === "Home" ? "01" : item.label === "Capture" ? "02" : item.label === "Memories" ? "03" : item.label === "Chat" ? "04" : "05"}
                  </span>
                </div>
              </Link>
            ))}
          </nav>

          <div className="mt-6 grid gap-3 md:grid-cols-2 lg:mt-auto lg:grid-cols-1">
            <SoftPanel>
              <p className="eyebrow">Storage</p>
              <p className="mt-3 text-sm leading-6 text-white">SQLite for metadata. Pinecone for vectors.</p>
            </SoftPanel>
            <SoftPanel>
              <p className="eyebrow">Mode</p>
              <p className="mt-3 text-sm leading-6 text-white">Single-user local build with no auth overhead.</p>
            </SoftPanel>
          </div>
        </aside>

        <main className="min-w-0 py-2">{children}</main>
      </div>
    </div>
  );
}
