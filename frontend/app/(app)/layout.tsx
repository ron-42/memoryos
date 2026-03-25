"use client";

import { ReactNode } from "react";

import { AppShell } from "@/components/shell";

export default function ProtectedLayout({ children }: { children: ReactNode }) {
  return <AppShell>{children}</AppShell>;
}
