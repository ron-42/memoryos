"use client";

import { env } from "@/lib/env";

export type CaptureEvent = {
  type: "progress" | "completed" | "error";
  stage: string;
  message: string;
  memory_id?: string | null;
  xp_awarded?: number | null;
  topics_updated?: string[] | null;
  connections_found?: number | null;
  metadata?: Record<string, unknown> | null;
};

type StreamCaptureOptions = {
  path: string;
  body?: BodyInit;
  headers?: HeadersInit;
  onEvent: (event: CaptureEvent) => void;
};

const apiBaseUrl = env.apiUrl.replace(/\/$/, "");

async function streamCapture({ path, body, headers, onEvent }: StreamCaptureOptions) {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    method: "POST",
    headers: {
      ...(headers ?? {})
    },
    body
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
      const dataLines = segment
        .split("\n")
        .filter((line) => line.startsWith("data:"))
        .map((line) => line.replace(/^data:\s*/, ""))
        .join("");

      if (!dataLines) {
        continue;
      }

      onEvent(JSON.parse(dataLines) as CaptureEvent);
    }
  }

  if (buffer.trim()) {
    const finalLine = buffer
      .split("\n")
      .find((line) => line.startsWith("data:"))
      ?.replace(/^data:\s*/, "");

    if (finalLine) {
      onEvent(JSON.parse(finalLine) as CaptureEvent);
    }
  }
}

export async function streamUrlCapture(url: string, onEvent: (event: CaptureEvent) => void) {
  await streamCapture({
    path: "/api/capture/url",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
    onEvent
  });
}

export async function streamTextCapture(
  text: string,
  title: string | null,
  onEvent: (event: CaptureEvent) => void
) {
  await streamCapture({
    path: "/api/capture/text",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, title }),
    onEvent
  });
}

export async function streamPdfCapture(file: File, onEvent: (event: CaptureEvent) => void) {
  const formData = new FormData();
  formData.append("file", file);

  await streamCapture({
    path: "/api/capture/pdf",
    body: formData,
    onEvent
  });
}
