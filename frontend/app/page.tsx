import Link from "next/link";

import { Badge, Panel, SoftPanel } from "@/components/ui";

export default function LandingPage() {
  return (
    <main className="min-h-screen px-4 py-4 text-white md:px-6">
      <div className="mx-auto grid min-h-[calc(100vh-2rem)] max-w-[1480px] gap-6 lg:grid-cols-[minmax(0,1.2fr)_24rem]">
        <Panel className="flex min-h-[42rem] flex-col justify-between">
          <div className="relative z-10">
            <Badge tone="accent">Personal Knowledge OS</Badge>
            <h1 className="mt-6 max-w-4xl text-5xl font-semibold leading-[0.92] text-white md:text-7xl">
              Build a memory system from what you actually consume.
            </h1>
            <p className="mt-6 max-w-2xl text-base leading-8 text-muted md:text-lg">
              Capture articles, PDFs, and pasted text. Turn them into structured memory with retrieval,
              connections, and visible learning momentum.
            </p>
          </div>

          <div className="relative z-10 mt-10 flex flex-wrap gap-4">
            <Link href="/home" className="btn-primary">
              Open workspace
            </Link>
            <Link href="/capture" className="btn-secondary">
              Start capturing
            </Link>
          </div>
        </Panel>

        <div className="grid gap-6">
          <SoftPanel className="min-h-[12rem]">
            <p className="eyebrow">Capture</p>
            <p className="mt-4 text-2xl font-semibold text-white">URL, PDF, text</p>
            <p className="mt-3 text-sm leading-6 text-muted">Streaming ingestion with summaries, chunks, embeddings, XP, and topic updates.</p>
          </SoftPanel>
          <SoftPanel className="min-h-[12rem]">
            <p className="eyebrow">Retrieve</p>
            <p className="mt-4 text-2xl font-semibold text-white">Grounded chat</p>
            <p className="mt-3 text-sm leading-6 text-muted">Ask your past self questions and get citations back instead of vague summaries.</p>
          </SoftPanel>
          <SoftPanel className="min-h-[12rem]">
            <p className="eyebrow">Connect</p>
            <p className="mt-4 text-2xl font-semibold text-white">Topic graph</p>
            <p className="mt-3 text-sm leading-6 text-muted">See which domains are compounding and where your memory network is getting denser.</p>
          </SoftPanel>
        </div>
      </div>
    </main>
  );
}
