"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";

import { PageFrame } from "@/components/page-frame";
import { Badge, EmptyState, Panel, SoftPanel } from "@/components/ui";
import { fetchMemoryDetail } from "@/lib/memory-api";

const blockedContentPhrases = [
  "warning: target url returned error 429",
  "too many requests",
  "our systems have detected unusual traffic from your computer network",
  "this page checks to see if it's really you sending the requests, and not a robot",
  "solve the above captcha"
];

function looksBlockedContent(value: string | null | undefined) {
  if (!value) {
    return false;
  }

  const lowered = value.toLowerCase();
  const hits = blockedContentPhrases.filter((phrase) => lowered.includes(phrase)).length;
  return lowered.includes("warning: target url returned error 429") || hits >= 2;
}

export default function MemoryDetailPage() {
  const params = useParams<{ id: string }>();
  const memoryId = Array.isArray(params.id) ? params.id[0] : params.id;
  const detailQuery = useQuery({
    queryKey: ["memory-detail", memoryId],
    queryFn: () => fetchMemoryDetail(memoryId),
    enabled: Boolean(memoryId),
  });
  const isBlockedMemory = detailQuery.data
    ? looksBlockedContent(
        [detailQuery.data.title, detailQuery.data.summary, detailQuery.data.raw_content].filter(Boolean).join("\n"),
      )
    : false;

  return (
    <PageFrame
      eyebrow="Memory"
      title="Memory detail"
      description="Inspect summary, extracted concepts, raw chunks, and related connections for a single memory."
    >
      {detailQuery.isLoading ? <p className="text-sm text-muted">Loading memory...</p> : null}
      {detailQuery.error ? <p className="text-sm text-rose-300">Failed to load memory detail.</p> : null}
      {detailQuery.data ? (
        <div className="space-y-6">
          <Panel>
            <div className="flex flex-wrap items-center gap-3">
              <Badge>{detailQuery.data.source_type}</Badge>
              {detailQuery.data.topic_tags.map((topic) => (
                <Badge key={topic} tone="accent">
                  {topic}
                </Badge>
              ))}
            </div>
            <h3 className="mt-5 text-3xl font-semibold">{isBlockedMemory ? "Capture unavailable" : detailQuery.data.title || "Untitled memory"}</h3>
            <p className="mt-4 text-sm leading-7 text-zinc-200">
              {isBlockedMemory
                ? "This source returned a rate-limit or bot-check page instead of usable content. Re-capture it later, use another URL, or paste the material as text."
                : detailQuery.data.summary || detailQuery.data.raw_content}
            </p>
            {detailQuery.data.source_url ? (
              <a
                href={detailQuery.data.source_url}
                target="_blank"
                rel="noreferrer"
                className="mt-4 inline-flex text-sm text-blue-300 transition hover:text-blue-200"
              >
                Open source
              </a>
            ) : null}
          </Panel>

          <div className="grid gap-4 lg:grid-cols-2">
            <Panel>
              <p className="eyebrow">Key concepts</p>
              <div className="mt-4 flex flex-wrap gap-2">
                {isBlockedMemory ? (
                  <p className="text-sm text-muted">Skipped because the source returned blocked content.</p>
                ) : detailQuery.data.key_concepts.length ? (
                  detailQuery.data.key_concepts.map((concept) => (
                    <span key={concept} className="badge badge-accent">
                      {concept}
                    </span>
                  ))
                ) : (
                  <p className="text-sm text-muted">No concepts extracted yet.</p>
                )}
              </div>
            </Panel>

            <Panel>
              <p className="eyebrow">Connections</p>
              <div className="mt-4 space-y-3">
                {detailQuery.data.connections.length ? (
                  detailQuery.data.connections.map((connection) => (
                    <SoftPanel key={connection.id}>
                      <p className="text-sm font-medium text-white">{connection.title || "Untitled connected memory"}</p>
                      <p className="mt-2 text-sm text-muted">{connection.connection_label || "Related through similarity search."}</p>
                    </SoftPanel>
                  ))
                ) : (
                  <EmptyState title="No connections stored yet" description="This memory has not been linked to other items yet." />
                )}
              </div>
            </Panel>
          </div>

          <Panel>
            <p className="eyebrow">Chunks</p>
            <div className="mt-4 space-y-3">
              {isBlockedMemory ? (
                <EmptyState
                  title="No usable chunks"
                  description="This memory contains a blocked or rate-limited capture response instead of source content."
                />
              ) : (
                detailQuery.data.chunks.map((chunk) => (
                  <SoftPanel key={chunk.id} className="text-sm leading-7 text-zinc-200">
                    {chunk.chunk_text}
                  </SoftPanel>
                ))
              )}
            </div>
          </Panel>
        </div>
      ) : null}
    </PageFrame>
  );
}
