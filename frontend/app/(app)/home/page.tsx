"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";

import { PageFrame } from "@/components/page-frame";
import { Badge, EmptyState, Panel, SoftPanel, StatTile } from "@/components/ui";
import { fetchStats } from "@/lib/dashboard-api";

export default function HomePage() {
  const statsQuery = useQuery({
    queryKey: ["stats"],
    queryFn: () => fetchStats(),
  });

  const stats = statsQuery.data;

  return (
    <PageFrame
      eyebrow="Dashboard"
      title="Overview"
      description="Recent progress, topic growth, and the latest connected memories."
    >
      {statsQuery.isLoading ? <p className="mb-4 text-sm text-muted">Loading dashboard...</p> : null}
      {statsQuery.error ? <p className="mb-4 text-sm text-rose-300">Failed to load dashboard.</p> : null}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatTile label="Current streak" value={`${stats?.current_streak ?? 0} days`} detail="Consecutive active days." tone="accent" />
        <StatTile label="XP today" value={`+${stats?.xp_today ?? 0}`} detail="New progress today." />
        <StatTile label="Total XP" value={`${stats?.total_xp ?? 0}`} detail="All captured progress." />
        <StatTile label="Longest streak" value={`${stats?.longest_streak ?? 0} days`} detail="Best run so far." tone="warm" />
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-[minmax(0,0.92fr)_minmax(0,1.08fr)]">
        <Panel>
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="eyebrow">Quick actions</p>
              <p className="mt-3 text-2xl font-semibold text-white">Next actions</p>
            </div>
            <Badge tone="accent">Live</Badge>
          </div>
          <div className="mt-6 grid gap-3 md:grid-cols-2">
            <Link href="/capture" className="surface-soft transition hover:border-white/15 hover:bg-white/[0.05]">
              <p className="eyebrow">Capture</p>
              <p className="mt-3 text-lg font-semibold text-white">Add a new memory</p>
              <p className="mt-3 text-sm leading-6 text-muted">Capture a URL, PDF, or note.</p>
            </Link>
            <Link href="/chat" className="surface-soft transition hover:border-white/15 hover:bg-white/[0.05]">
              <p className="eyebrow">Retrieve</p>
              <p className="mt-3 text-lg font-semibold text-white">Ask a question</p>
              <p className="mt-3 text-sm leading-6 text-muted">Search your stored context with citations.</p>
            </Link>
          </div>
        </Panel>

        <Panel>
          <p className="eyebrow">Top topics</p>
          <p className="mt-3 text-2xl font-semibold text-white">Topic growth</p>
          <div className="mt-4 space-y-4">
            {stats?.top_topics.length ? (
              stats.top_topics.map((topic) => (
                <div key={topic.id} className="surface-soft">
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-sm font-medium text-white">{topic.name}</p>
                    <Badge tone="accent">Level {topic.level}</Badge>
                  </div>
                  <div className="mt-4 flex items-center justify-between gap-3 text-xs uppercase tracking-[0.18em] text-muted">
                    <span>{topic.memory_count} memories</span>
                    <span>{topic.total_xp} XP</span>
                  </div>
                  <div className="mt-4 h-2 rounded-full bg-white/5">
                    <div
                      className="h-2 rounded-full"
                      style={{
                        width: `${Math.min(100, (topic.total_xp / 3500) * 100)}%`,
                        backgroundColor: topic.color ?? "#3b82f6",
                      }}
                    />
                  </div>
                </div>
              ))
            ) : (
              <EmptyState title="No topics yet" description="Capture a few items first. Topic progression will start appearing after ingestion." />
            )}
          </div>
        </Panel>
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)]">
        <Panel>
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="eyebrow">Recent captures</p>
              <p className="mt-3 text-2xl font-semibold text-white">Recent captures</p>
            </div>
            <Link href="/memories" className="btn-secondary">
              Open library
            </Link>
          </div>
          <div className="mt-4 space-y-3">
            {stats?.recent_captures.length ? (
              stats.recent_captures.map((memory) => (
                <Link key={memory.id} href={`/memories/${memory.id}`} className="surface-soft block transition hover:border-white/15 hover:bg-white/[0.05]">
                  <div className="flex items-center justify-between gap-3">
                    <Badge>{memory.source_type}</Badge>
                    <span className="text-xs uppercase tracking-[0.18em] text-muted">{memory.topic_tags.length} topics</span>
                  </div>
                  <p className="mt-4 text-lg font-semibold text-white">{memory.title || "Untitled memory"}</p>
                  <p className="mt-3 text-sm text-muted">{memory.topic_tags.join(", ") || "No topics yet"}</p>
                </Link>
              ))
            ) : (
              <EmptyState title="No captures yet" description="Start with the capture screen and the library will populate here." />
            )}
          </div>
        </Panel>

        <Panel>
          <p className="eyebrow">Recent connections</p>
          <p className="mt-3 text-2xl font-semibold text-white">Recent connections</p>
          <div className="mt-4 space-y-3">
            {stats?.recent_connections.length ? (
              stats.recent_connections.map((connection) => (
                <SoftPanel key={connection.id}>
                  <p className="text-sm font-medium text-white">
                    <span className="text-muted">Similarity {connection.similarity_score.toFixed(2)}</span>
                  </p>
                  <p className="mt-3 text-base font-medium text-white">
                  {connection.memory_a_title || "Untitled memory"} <span className="text-muted">to</span>{" "}
                  {connection.memory_b_title || "Untitled memory"}
                  </p>
                  <p className="mt-3 text-sm leading-6 text-muted">
                    {connection.connection_label || "Related through similarity search."}
                  </p>
                </SoftPanel>
              ))
            ) : (
              <EmptyState title="No connections yet" description="Once the system has enough memory density, discovered relationships will show up here." />
            )}
          </div>
        </Panel>
      </div>
    </PageFrame>
  );
}
