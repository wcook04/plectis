import type { Node } from 'reactflow';

export type FlowPaneSize = Pick<HTMLDivElement, 'clientWidth' | 'clientHeight'>;

function numericDimension(value: number | string | null | undefined, fallback: number): number {
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (typeof value === 'string') {
    const parsed = Number.parseFloat(value);
    if (Number.isFinite(parsed)) return parsed;
  }
  return fallback;
}

export function nodeSize(node: Node): { width: number; height: number } {
  const style = node.style as { width?: number | string; height?: number | string } | undefined;
  return {
    width: numericDimension(style?.width ?? node.width, 260),
    height: numericDimension(style?.height ?? node.height, 92),
  };
}

function nodeFrame(nodes: Node[]): { minX: number; minY: number; maxX: number; maxY: number; width: number; height: number } | null {
  if (!nodes.length) return null;
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  nodes.forEach((node) => {
    const size = nodeSize(node);
    minX = Math.min(minX, node.position.x);
    minY = Math.min(minY, node.position.y);
    maxX = Math.max(maxX, node.position.x + size.width);
    maxY = Math.max(maxY, node.position.y + size.height);
  });
  return {
    minX,
    minY,
    maxX,
    maxY,
    width: Math.max(1, maxX - minX),
    height: Math.max(1, maxY - minY),
  };
}

function nodeBounds(nodes: Node[]): { width: number; height: number } | null {
  const frame = nodeFrame(nodes);
  return frame ? { width: frame.width, height: frame.height } : null;
}

export function focusCameraZoom(nodes: Node[], pane: HTMLDivElement | null, fallbackZoom: number): number {
  const bounds = nodeBounds(nodes);
  if (!bounds || !pane) return Math.min(Math.max(fallbackZoom || 0.62, 0.58), 0.78);
  const fitX = (pane.clientWidth - 96) / bounds.width;
  const fitY = (pane.clientHeight - 96) / bounds.height;
  const fitted = Math.min(fitX, fitY);
  // Focus mode is a SELECTED-PACKET inspection view, not a fit-the-whole-ego
  // poster. A tall ego column used to pull the fitted zoom down to ~0.54, which
  // rendered the focused node + its immediate neighbors near-illegible at first
  // paint (large dead canvas, ~7px labels). Floor the opening zoom so the
  // selection and its first-order neighborhood read on load; the operator pans
  // for the long tail (already surfaced as ego "+hidden" chips). Centering on
  // the selected node is preserved by focusViewportForSelectedNode.
  const minReadableZoom = pane.clientWidth < 760 ? 0.5 : 0.62;
  const maxReadableZoom = pane.clientWidth < 760 ? 0.66 : 0.8;
  return Math.min(Math.max(fitted, minReadableZoom), maxReadableZoom);
}

// Density-tiered opening zoom for the directed (dagre) modes — blast / evidence.
// fitView() on a 150-node dagre graph shrinks every card into an illegible
// vertical strip (the documented blast-view failure). Instead we open centered
// on the selected spine at a zoom where the focus node + its immediate
// neighbors stay readable, and let the operator pan / zoom out for the long
// tail. The denser the graph, the lower (but never microscopic) the floor.
export function readableDirectedZoom(pane: FlowPaneSize | null, nodeCount: number): number {
  const wide = (pane?.clientWidth ?? 0) >= 1200;
  if (nodeCount > 90) return wide ? 0.6 : 0.48; // overview tier
  if (nodeCount > 36) return wide ? 0.72 : 0.56; // packet tier
  return wide ? 0.9 : 0.72; // detail tier
}

export function focusViewportForSelectedNode(
  selectedNode: Node,
  pane: FlowPaneSize,
  zoom: number,
): { x: number; y: number; zoom: number } {
  const { width, height } = nodeSize(selectedNode);
  const nodeCenterX = selectedNode.position.x + width / 2;
  const nodeCenterY = selectedNode.position.y + height / 2;
  return {
    x: pane.clientWidth / 2 - nodeCenterX * zoom,
    y: pane.clientHeight / 2 - nodeCenterY * zoom,
    zoom,
  };
}

// Panorama / System Atlas: the whole board IS the artifact, so unlike the
// directed modes we DO fit everything — the hero "see the entire system" shot.
// The board is wide, so the fitted zoom can be small; we floor it gently so the
// district hulls and their headers stay readable on open, and the operator
// zooms into a district for the file marks. Centered with a margin so no
// district is clipped to the pane edge.
export function panoramaViewport(
  nodes: Node[],
  pane: HTMLDivElement | null,
): { x: number; y: number; zoom: number } | null {
  const frame = nodeFrame(nodes);
  if (!frame || !pane) return null;
  const margin = 64;
  const fitX = (pane.clientWidth - margin * 2) / frame.width;
  const fitY = (pane.clientHeight - margin * 2) / frame.height;
  const zoom = Math.min(Math.max(Math.min(fitX, fitY), 0.05), 0.7);
  const graphWidth = frame.width * zoom;
  const graphHeight = frame.height * zoom;
  return {
    x: (pane.clientWidth - graphWidth) / 2 - frame.minX * zoom,
    y: Math.max(margin / 2, (pane.clientHeight - graphHeight) / 2) - frame.minY * zoom,
    zoom,
  };
}

export function architectureViewport(
  nodes: Node[],
  pane: HTMLDivElement | null,
): { x: number; y: number; zoom: number } | null {
  const frame = nodeFrame(nodes);
  if (!frame || !pane) return null;
  // Wide-pane architecture fit floored at 0.68 (was 0.56): at >=1200px the board
  // was pinned to 0.56, shrinking cluster-card text below ~7px; 0.68 lifts it to
  // legible without changing layout (x/y offsets below derive from zoom).
  const zoom = pane.clientWidth < 760 ? 0.42 : pane.clientWidth < 1200 ? 0.5 : 0.68;
  const graphWidth = frame.width * zoom;
  const x = graphWidth < pane.clientWidth
    ? (pane.clientWidth - graphWidth) / 2 - frame.minX * zoom
    : 32 - frame.minX * zoom;
  return {
    x,
    y: 28 - frame.minY * zoom,
    zoom,
  };
}
