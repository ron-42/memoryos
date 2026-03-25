"use client";

import { useQuery } from "@tanstack/react-query";

import { PageFrame } from "@/components/page-frame";
import { TopicGraph } from "@/components/topic-graph";
import { Badge, EmptyState, Panel, StatTile } from "@/components/ui";
import { fetchGraph } from "@/lib/dashboard-api";

export default function GraphPage() {
  const graphQuery = useQuery({
    queryKey: ["graph"],
    queryFn: () => fetchGraph(),
  });

  return (
    <PageFrame
      eyebrow="Graph"
      title="Your mind visualized"
      description="Topic nodes and connection edges rendered from stored memories so you can see where your learning clusters are forming."
    >
      {graphQuery.isLoading ? <p className="mb-4 text-sm text-muted">Loading graph...</p> : null}
      {graphQuery.error ? <p className="mb-4 text-sm text-rose-300">Failed to load graph.</p> : null}
      {graphQuery.data ? (
        <>
          <div className="mb-6 grid gap-4 md:grid-cols-3">
            <StatTile label="Nodes" value={`${graphQuery.data.nodes.length}`} detail="Distinct topics currently represented in the graph." tone="accent" />
            <StatTile label="Edges" value={`${graphQuery.data.edges.length}`} detail="Relationship lines discovered between topics." />
            <StatTile
              label="Strongest link"
              value={`${Math.max(0, ...graphQuery.data.edges.map((edge) => edge.strength)).toFixed(2)}`}
              detail="Highest edge strength currently present in the graph."
              tone="warm"
            />
          </div>

          <TopicGraph graph={graphQuery.data} />
          <div className="mt-6 grid gap-4 md:grid-cols-3">
            {graphQuery.data.nodes.slice(0, 6).map((node) => (
              <Panel key={node.id}>
                <div className="flex items-center gap-3">
                  <span className="h-3 w-3 rounded-full" style={{ backgroundColor: node.color }} />
                  <p className="text-sm font-medium text-white">{node.label}</p>
                </div>
                <div className="mt-4 flex flex-wrap gap-2">
                  <Badge tone="accent">{node.memory_count} memories</Badge>
                  <Badge tone="warm">Level {node.level}</Badge>
                </div>
              </Panel>
            ))}
          </div>
        </>
      ) : (
        <EmptyState title="No graph data yet" description="Capture a few items and let topic aggregation run before expecting a meaningful graph." />
      )}
    </PageFrame>
  );
}
