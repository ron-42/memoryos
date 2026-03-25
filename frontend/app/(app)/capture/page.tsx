"use client";

import { ChangeEvent, FormEvent, useMemo, useState } from "react";

import { PageFrame } from "@/components/page-frame";
import { Badge, Panel, SoftPanel } from "@/components/ui";
import { CaptureEvent, streamPdfCapture, streamTextCapture, streamUrlCapture } from "@/lib/api";

type CaptureMode = "url" | "text" | "pdf";

function isYouTubeUrl(value: string) {
  try {
    const { hostname } = new URL(value.trim());
    return hostname.includes("youtube.com") || hostname.includes("youtu.be");
  } catch {
    return false;
  }
}

export default function CapturePage() {
  const [mode, setMode] = useState<CaptureMode>("url");
  const [value, setValue] = useState("");
  const [title, setTitle] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [events, setEvents] = useState<CaptureEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isCapturing, setIsCapturing] = useState(false);

  const completedEvent = useMemo(
    () => [...events].reverse().find((event) => event.type === "completed") ?? null,
    [events]
  );

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    setFile(event.target.files?.[0] ?? null);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (mode === "url" && !value.trim()) {
      setError("Paste a URL first.");
      return;
    }

    if (mode === "url" && isYouTubeUrl(value)) {
      setError("YouTube URLs are out of scope for v1. Use article URLs, PDFs, or pasted text.");
      return;
    }

    if (mode === "text" && value.trim().length < 20) {
      setError("Pasted text should be at least 20 characters.");
      return;
    }

    if (mode === "pdf" && !file) {
      setError("Choose a PDF file first.");
      return;
    }

    setIsCapturing(true);
    setError(null);
    setEvents([]);

    const onEvent = (nextEvent: CaptureEvent) => {
      setEvents((current) => [...current, nextEvent]);
      if (nextEvent.type === "error") {
        setError(nextEvent.message);
      }
    };

    try {
      if (mode === "url") {
        await streamUrlCapture(value.trim(), onEvent);
      } else if (mode === "text") {
        await streamTextCapture(value.trim(), title.trim() || null, onEvent);
      } else if (file) {
        await streamPdfCapture(file, onEvent);
      }
    } catch (streamError) {
      setError(streamError instanceof Error ? streamError.message : "Capture failed");
    } finally {
      setIsCapturing(false);
    }
  }

  return (
    <PageFrame
      eyebrow="Capture"
      title="Capture memory"
      description="Keep v1 narrow: article URLs, PDFs, and pasted text."
    >
      <div className="mb-6 flex flex-wrap gap-2">
        {(["url", "text", "pdf"] as CaptureMode[]).map((item) => (
          <button
            key={item}
            type="button"
            onClick={() => setMode(item)}
            className={`tab-trigger ${
              mode === item ? "tab-trigger-active" : ""
            }`}
          >
            {item === "url" ? "URL" : item === "text" ? "Text" : "PDF"}
          </button>
        ))}
      </div>
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1.2fr)_minmax(18rem,0.8fr)]">
        <Panel>
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="eyebrow">Source</p>
              <p className="mt-3 text-2xl font-semibold text-white">Add a new item</p>
            </div>
            <Badge tone={mode === "pdf" ? "warm" : "accent"}>{mode}</Badge>
          </div>

          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            {mode !== "pdf" ? (
              <>
                {mode === "text" ? (
                  <input
                    value={title}
                    onChange={(event) => setTitle(event.target.value)}
                    placeholder="Optional title"
                    className="input-field"
                  />
                ) : null}
                <textarea
                  value={value}
                  onChange={(event) => setValue(event.target.value)}
                  placeholder={mode === "url" ? "Paste a URL" : "Paste text you want to remember"}
                  className="textarea-field"
                />
              </>
            ) : (
              <label className="file-drop cursor-pointer border border-dashed border-white/10">
                <div>
                  <p className="text-sm font-medium text-white">{file ? file.name : "Choose a PDF to capture"}</p>
                  <p className="mt-2 text-sm leading-6 text-muted">Scanned PDFs remain out of scope for v1. Native text PDFs work.</p>
                </div>
                <input type="file" accept="application/pdf" onChange={handleFileChange} className="hidden" />
              </label>
            )}

            <div className="flex items-center gap-3">
              <button type="submit" disabled={isCapturing} className="btn-primary btn-primary-accent">
                {isCapturing ? "Capturing..." : "Capture"}
              </button>
              <span className="text-sm text-muted">Streaming status updates appear on the right.</span>
            </div>

            {error ? <p className="text-sm text-rose-300">{error}</p> : null}
          </form>
        </Panel>

        <div className="space-y-4">
          <Panel>
            <div className="flex items-center justify-between gap-3">
              <p className="eyebrow">Stream</p>
              <Badge tone="accent">{events.length} events</Badge>
            </div>
            <div className="mt-4 space-y-3">
              {events.length ? (
                events.map((event, index) => (
                  <SoftPanel key={`${event.stage}-${index}`}>
                    <div className="flex items-center justify-between gap-3">
                      <p className="text-sm font-medium capitalize">{event.stage}</p>
                      <span
                        className={`rounded-full px-2.5 py-1 text-[11px] uppercase tracking-[0.2em] ${
                          event.type === "completed"
                            ? "bg-blue-500/15 text-blue-100"
                            : event.type === "error"
                              ? "bg-rose-500/15 text-rose-200"
                              : "bg-white/10 text-zinc-300"
                        }`}
                      >
                        {event.type}
                      </span>
                    </div>
                    <p className="mt-2 text-sm text-muted">{event.message}</p>
                  </SoftPanel>
                ))
              ) : (
                <p className="text-sm text-muted">No capture has started yet.</p>
              )}
            </div>
          </Panel>

          <Panel>
            <p className="eyebrow">Result</p>
            {completedEvent ? (
              <div className="mt-4 grid gap-3 sm:grid-cols-3">
                <SoftPanel>
                  <p className="eyebrow">XP gained</p>
                  <p className="mt-3 text-3xl font-semibold">{completedEvent.xp_awarded ?? 0}</p>
                </SoftPanel>
                <SoftPanel>
                  <p className="eyebrow">Topics updated</p>
                  <p className="mt-2 text-sm text-white">
                    {completedEvent.topics_updated?.length ? completedEvent.topics_updated.join(", ") : "None"}
                  </p>
                </SoftPanel>
                <SoftPanel>
                  <p className="eyebrow">Connections found</p>
                  <p className="mt-3 text-3xl font-semibold">{completedEvent.connections_found ?? 0}</p>
                </SoftPanel>
              </div>
            ) : (
              <p className="mt-4 text-sm text-muted">Completed capture details will appear here.</p>
            )}
          </Panel>
        </div>
      </div>
    </PageFrame>
  );
}
