"use client";

import { GraphResponse } from "@/lib/dashboard-api";
import { Panel } from "@/components/ui";

type PositionedNode = GraphResponse["nodes"][number] & {
  x: number;
  y: number;
};

function polarLayout(nodes: GraphResponse["nodes"], width: number, height: number): PositionedNode[] {
  if (!nodes.length) {
    return [];
  }
  const centerX = width / 2;
  const centerY = height / 2;
  const radius = Math.min(width, height) * 0.32;

  return nodes.map((node, index) => {
    const angle = (Math.PI * 2 * index) / nodes.length;
    return {
      ...node,
      x: centerX + Math.cos(angle) * radius,
      y: centerY + Math.sin(angle) * radius,
    };
  });
}

export function TopicGraph({ graph }: { graph: GraphResponse }) {
  const width = 920;
  const height = 520;
  const nodes = polarLayout(graph.nodes, width, height);
  const nodeMap = new Map(nodes.map((node) => [node.id, node]));

  return (
    <Panel className="overflow-hidden p-4">
      <svg viewBox={`0 0 ${width} ${height}`} className="h-[28rem] w-full">
        <defs>
          <radialGradient id="graphGlow" cx="50%" cy="50%" r="60%">
            <stop offset="0%" stopColor="rgba(120,215,196,0.18)" />
            <stop offset="100%" stopColor="rgba(120,215,196,0)" />
          </radialGradient>
        </defs>
        <rect x="0" y="0" width={width} height={height} fill="url(#graphGlow)" />
        {graph.edges.map((edge) => {
          const source = nodeMap.get(edge.source);
          const target = nodeMap.get(edge.target);
          if (!source || !target) {
            return null;
          }
          return (
            <line
              key={`${edge.source}-${edge.target}`}
              x1={source.x}
              y1={source.y}
              x2={target.x}
              y2={target.y}
              stroke="rgba(207, 233, 227, 0.22)"
              strokeWidth={Math.max(1, edge.strength * 4)}
            />
          );
        })}
        {nodes.map((node) => (
          <g key={node.id} transform={`translate(${node.x}, ${node.y})`}>
            <circle r={Math.max(18, Math.min(44, 12 + node.memory_count * 2))} fill={node.color} fillOpacity="0.8" />
            <circle r={Math.max(18, Math.min(44, 12 + node.memory_count * 2)) + 8} fill={node.color} fillOpacity="0.08" />
            <text
              x="0"
              y="4"
              textAnchor="middle"
              fontSize="11"
              fill="white"
              className="tracking-wide"
            >
              {node.label}
            </text>
          </g>
        ))}
      </svg>
    </Panel>
  );
}
