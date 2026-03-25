"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { PageFrame } from "@/components/page-frame";
import { Badge, EmptyState, SoftPanel } from "@/components/ui";
import { fetchMemories } from "@/lib/memory-api";

export default function MemoriesPage() {
  const [search, setSearch] = useState("");

  const queryKey = useMemo(() => ["memories", search], [search]);
  const memoriesQuery = useQuery({
    queryKey,
    queryFn: () => fetchMemories(search),
  });

  return (
    <PageFrame
      eyebrow="Library"
      title="Your captured memory"
      description="Browse the memory library, filter by title, and jump into the detail page for summaries, chunks, and linked items."
    >
      <input
        value={search}
        onChange={(event) => setSearch(event.target.value)}
        placeholder="Search memory titles"
        className="input-field mb-6"
      />
      {memoriesQuery.isLoading ? <p className="text-sm text-muted">Loading memories...</p> : null}
      {memoriesQuery.error ? <p className="text-sm text-rose-300">Failed to load memories.</p> : null}
      <div className="grid gap-4 md:grid-cols-2">
        {memoriesQuery.data?.items.length ? (
          memoriesQuery.data.items.map((memory) => (
            <Link key={memory.id} href={`/memories/${memory.id}`} className="block transition hover:-translate-y-0.5">
              <SoftPanel className="h-full hover:border-white/15 hover:bg-white/[0.05]">
                <div className="flex items-center justify-between gap-3">
                  <Badge>{memory.source_type}</Badge>
                  <span className="text-xs uppercase tracking-[0.18em] text-muted">
                    {memory.topic_tags.length} topics
                  </span>
                </div>
                <h3 className="mt-4 text-2xl font-semibold text-white">{memory.title || "Untitled memory"}</h3>
                <p className="mt-3 text-sm leading-6 text-muted">{memory.topic_tags.join(", ") || "No topics yet"}</p>
              </SoftPanel>
            </Link>
          ))
        ) : (
          <div className="md:col-span-2">
            <EmptyState title="No memories found" description="Try a different search or capture a few sources so the library has something to index." />
          </div>
        )}
      </div>
    </PageFrame>
  );
}
