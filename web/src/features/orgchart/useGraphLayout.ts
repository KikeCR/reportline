// The bundled build avoids elkjs's Node-oriented `main.js`, whose
// `require('web-worker')` call (only reached if `workerUrl` is set, which
// we never do) fails to resolve under Vite's production build even though
// it's never actually invoked at runtime - see docs/adr entry for Phase 3.
import ELK from 'elkjs/lib/elk.bundled.js'
import { useEffect, useState } from 'react'

import type { GraphOut } from '../../api/schemas'
import {
	buildElkGraph,
	computeHiddenIds,
	computePrimaryChildren,
	overlayEdgePoints,
	visibleNodesOf,
} from './graphMapping'
import {
	NODE_HEIGHT,
	NODE_WIDTH,
	type LaidOutGraph,
	type PositionedEdge,
	type PositionedNode,
} from './types'

const elk = new ELK()

/** Runs elkjs (layered, top-down, primary-solid-edges-only skeleton) and
 * attaches straight anchor-to-anchor points for every overlay edge using
 * the positions elk computed. Returns null while the first layout is
 * still pending. */
export function useGraphLayout(
	graph: GraphOut | undefined,
	collapsedIds: ReadonlySet<string>,
	filterHiddenIds: ReadonlySet<string>,
): LaidOutGraph | null {
	const [layout, setLayout] = useState<LaidOutGraph | null>(null)

	useEffect(() => {
		if (!graph) {
			return
		}

		let cancelled = false
		const hiddenIds = new Set([
			...computeHiddenIds(graph.edges, collapsedIds),
			...filterHiddenIds,
		])
		const visibleNodes = visibleNodesOf(graph, hiddenIds)
		const childrenByManagerId = computePrimaryChildren(graph.edges)
		const elkGraph = buildElkGraph(visibleNodes, graph.edges)

		void elk.layout(elkGraph).then((result) => {
			if (cancelled) return

			const positionById = new Map(
				(result.children ?? []).map((child) => [
					child.id,
					{ x: child.x ?? 0, y: child.y ?? 0 },
				]),
			)

			const nodes: PositionedNode[] = visibleNodes.map((node) => {
				const position = positionById.get(node.id) ?? { x: 0, y: 0 }
				return {
					...node,
					x: position.x,
					y: position.y,
					width: NODE_WIDTH,
					height: NODE_HEIGHT,
					hasChildren: (childrenByManagerId.get(node.id)?.length ?? 0) > 0,
					collapsed: collapsedIds.has(node.id),
				}
			})
			const nodeById = new Map(nodes.map((n) => [n.id, n]))
			const visibleIds = new Set(visibleNodes.map((n) => n.id))

			const edges: PositionedEdge[] = []
			for (const edge of graph.edges) {
				if (
					!visibleIds.has(edge.manager_id) ||
					!visibleIds.has(edge.report_id)
				) {
					continue
				}
				const manager = nodeById.get(edge.manager_id)
				const report = nodeById.get(edge.report_id)
				if (!manager || !report) continue
				edges.push({
					...edge,
					id: `${edge.manager_id}->${edge.report_id}->${edge.relation}`,
					points: overlayEdgePoints(manager, report),
				})
			}

			const width = nodes.reduce((max, n) => Math.max(max, n.x + n.width), 0)
			const height = nodes.reduce((max, n) => Math.max(max, n.y + n.height), 0)

			setLayout({ nodes, edges, width, height })
		})

		return () => {
			cancelled = true
		}
	}, [graph, collapsedIds, filterHiddenIds])

	return graph ? layout : null
}
