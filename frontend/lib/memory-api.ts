"use client";

import { env } from "@/lib/env";

export type MemorySummary = {
  id: string;
  title: string | null;
  source_type: string;
  source_url: string | null;
  topic_tags: string[];
  content_type: string | null;
  importance_score: number | null;
  created_at: string;
};

export type MemoryDetail = {
  id: string;
  title: string | null;
  source_type: string;
  source_url: string | null;
  source_title: string | null;
  summary: string | null;
  raw_content: string;
  key_concepts: string[];
  topic_tags: string[];
  content_type: string | null;
  importance_score: number | null;
  estimated_read_time: number | null;
  xp_awarded: number;
  created_at: string;
  connections: Array<{
    id: string;
    memory_id: string;
    title: string | null;
    similarity_score: number;
    connection_label: string | null;
  }>;
  chunks: Array<{
    id: string;
    chunk_index: number;
    chunk_text: string;
  }>;
};

export type ChatCitation = {
  memory_id: string;
  title: string | null;
  source_url: string | null;
  similarity: number;
  excerpt: string;
};

export type ChatStreamEvent =
  | { type: "progress"; stage?: string; message: string }
  | { type: "chunk"; content: string }
  | { type: "completed"; answer: string; citations: ChatCitation[] };

const apiBaseUrl = env.apiUrl.replace(/\/$/, "");

async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`);

  if (!response.ok) {
    throw new Error(await response.text() || `Request failed with status ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export async function fetchMemories(query?: string) {
  const suffix = query?.trim() ? `?q=${encodeURIComponent(query.trim())}` : "";
  return apiGet<{ items: MemorySummary[]; next_cursor: string | null; limit: number }>(`/api/memories${suffix}`);
}

export async function fetchMemoryDetail(memoryId: string) {
  return apiGet<MemoryDetail>(`/api/memories/${memoryId}`);
}

export async function streamChat(
  query: string,
  onEvent: (event: ChatStreamEvent) => void,
) {
  const response = await fetch(`${apiBaseUrl}/api/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ query })
  });

  if (!response.ok) {
    throw new Error(await response.text() || `Request failed with status ${response.status}`);
  }

  if (!response.body) {
    throw new Error("Streaming response body is missing");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    const segments = buffer.split("\n\n");
    buffer = segments.pop() ?? "";

    for (const segment of segments) {
      const line = segment
        .split("\n")
        .find((item) => item.startsWith("data:"))
        ?.replace(/^data:\s*/, "");

      if (line) {
        onEvent(JSON.parse(line) as ChatStreamEvent);
      }
    }
  }

  if (buffer.trim()) {
    const finalLine = buffer
      .split("\n")
      .find((item) => item.startsWith("data:"))
      ?.replace(/^data:\s*/, "");

    if (finalLine) {
      onEvent(JSON.parse(finalLine) as ChatStreamEvent);
    }
  }
}
