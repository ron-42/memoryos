"use client";

import { env } from "@/lib/env";

export type TopicProgress = {
  id: string;
  name: string;
  memory_count: number;
  total_xp: number;
  level: number;
  color: string | null;
};

export type RecentConnection = {
  id: string;
  similarity_score: number;
  connection_label: string | null;
  discovered_at: string;
  memory_a_id: string;
  memory_a_title: string | null;
  memory_b_id: string;
  memory_b_title: string | null;
};

export type StatsResponse = {
  current_streak: number;
  longest_streak: number;
  total_xp: number;
  xp_today: number;
  top_topics: TopicProgress[];
  recent_captures: Array<{
    id: string;
    title: string | null;
    source_type: string;
    source_url: string | null;
    topic_tags: string[];
    content_type: string | null;
    importance_score: number | null;
    created_at: string;
  }>;
  recent_connections: RecentConnection[];
};

export type GraphResponse = {
  nodes: Array<{
    id: string;
    label: string;
    level: number;
    memory_count: number;
    color: string;
  }>;
  edges: Array<{
    source: string;
    target: string;
    strength: number;
  }>;
};

const apiBaseUrl = env.apiUrl.replace(/\/$/, "");

async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`);

  if (!response.ok) {
    throw new Error(await response.text() || `Request failed with status ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export async function fetchStats() {
  return apiGet<StatsResponse>("/api/stats");
}

export async function fetchTopics() {
  return apiGet<{ items: TopicProgress[] }>("/api/topics");
}

export async function fetchGraph() {
  return apiGet<GraphResponse>("/api/graph");
}
