import type { Metadata } from "next";
import type { ReactNode } from "react";

import "@/styles/globals.css";
import { Providers } from "@/lib/providers";

export const metadata: Metadata = {
  title: "MemoryOS",
  description: "Capture what you learn. Retrieve what matters."
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
