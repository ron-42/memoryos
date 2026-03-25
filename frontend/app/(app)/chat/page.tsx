"use client";

import { FormEvent, useState } from "react";

import { PageFrame } from "@/components/page-frame";
import { Badge, Panel, SoftPanel } from "@/components/ui";
import { ChatCitation, streamChat } from "@/lib/memory-api";

export default function ChatPage() {
  const [query, setQuery] = useState("");
  const [answer, setAnswer] = useState("");
  const [citations, setCitations] = useState<ChatCitation[]>([]);
  const [status, setStatus] = useState("Ask what you know.");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!query.trim()) {
      setError("Enter a question first.");
      return;
    }

    setAnswer("");
    setCitations([]);
    setError(null);
    setStatus("Starting retrieval");
    setIsLoading(true);

    try {
      await streamChat(query.trim(), (nextEvent) => {
        if (nextEvent.type === "progress") {
          setStatus(nextEvent.message);
          return;
        }
        if (nextEvent.type === "chunk") {
          setAnswer((current) => current + nextEvent.content);
          return;
        }
        setAnswer(nextEvent.answer);
        setCitations(nextEvent.citations);
        setStatus("Completed");
      });
    } catch (streamError) {
      setError(streamError instanceof Error ? streamError.message : "Chat failed");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <PageFrame
      eyebrow="Chat"
      title="Ask a question"
      description="Grounded answers stream from retrieval over your stored memories, with citations alongside the response."
    >
      <Panel className="mb-4">
        <form onSubmit={handleSubmit} className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_auto]">
          <textarea
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="What do I know about retrieval augmented generation?"
            className="textarea-field min-h-[8rem]"
          />
          <div className="flex flex-col justify-between gap-3">
            <Badge tone="accent">Streaming</Badge>
            <button type="submit" disabled={isLoading} className="btn-primary btn-primary-accent">
              {isLoading ? "Thinking..." : "Ask"}
            </button>
          </div>
        </form>
      </Panel>

      {error ? <p className="mb-4 text-sm text-rose-300">{error}</p> : null}
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <Panel className="min-h-96">
          <div className="flex items-center justify-between gap-3">
            <p className="eyebrow">Answer</p>
            <Badge tone={isLoading ? "accent" : "default"}>{status}</Badge>
          </div>
          <div className="mt-6 whitespace-pre-wrap text-sm leading-7 text-zinc-100">
            {answer || "Your grounded answer will stream here."}
          </div>
        </Panel>
        <Panel>
          <p className="eyebrow">Sources</p>
          <div className="mt-4 space-y-3">
            {citations.length ? (
              citations.map((citation) => (
                <SoftPanel key={`${citation.memory_id}-${citation.title ?? "untitled"}`}>
                  <Badge tone="warm">Similarity {citation.similarity.toFixed(2)}</Badge>
                  <p className="mt-4 text-sm font-medium text-white">{citation.title || "Untitled memory"}</p>
                  <p className="mt-2 text-sm text-muted">{citation.excerpt}</p>
                </SoftPanel>
              ))
            ) : (
              <p className="text-sm text-muted">Retrieved memories will appear here.</p>
            )}
          </div>
        </Panel>
      </div>
    </PageFrame>
  );
}
