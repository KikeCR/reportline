/**
 * Pure graph data mapping - no elkjs, no DOM, no React. Kept separate from
 * `useGraphLayout` (which calls elkjs) so the tree/filter logic here is
 * cheap to unit test without a layout engine in the loop.
 */
import type { ElkExtendedEdge, ElkNode } from 'elkjs/lib/elk-api'

import type { EdgeOut, GraphOut, NodeOut } from '../../api/schemas'
import { NODE_HEIGHT, NODE_WIDTH, type Point } from './types'

/** Every node's skeleton (primary solid) manager, if it has one. */
export function computePrimaryParents(edges: EdgeOut[]): Map<string, string> {
	const parentByReportId = new Map<string, string>()
	for (const edge of edges) {
		if (edge.relation === 'solid' && edge.is_primary) {
			parentByReportId.set(edge.report_id, edge.manager_id)
		}
	}
	return parentByReportId
}

/** Skeleton children of every manager, derived from the same primary edges. */
export function computePrimaryChildren(
	edges: EdgeOut[],
): Map<string, string[]> {
	const childrenByManagerId = new Map<string, string[]>()
	for (const edge of edges) {
		if (edge.relation === 'solid' && edge.is_primary) {
			const siblings = childrenByManagerId.get(edge.manager_id) ?? []
			siblings.push(edge.report_id)
			childrenByManagerId.set(edge.manager_id, siblings)
		}
	}
	return childrenByManagerId
}

/**
 * Every node hidden because one of its skeleton ancestors is collapsed.
 * A collapsed node itself stays visible - only its descendants hide.
 */
export function computeHiddenIds(
	edges: EdgeOut[],
	collapsedIds: ReadonlySet<string>,
): Set<string> {
	const childrenByManagerId = computePrimaryChildren(edges)
	const hidden = new Set<string>()

	function hideSubtree(managerId: string): void {
		for (const childId of childrenByManagerId.get(managerId) ?? []) {
			if (!hidden.has(childId)) {
				hidden.add(childId)
				hideSubtree(childId)
			}
		}
	}

	for (const collapsedId of collapsedIds) {
		hideSubtree(collapsedId)
	}
	return hidden
}

/** Node ids that don't match the selected department filter - hidden
 * entirely from the layout so the matching subset is easy to read. */
export function computeDepartmentFilterHiddenIds(
	nodes: NodeOut[],
	department: string | null,
): Set<string> {
	if (!department) return new Set()
	return new Set(
		nodes.filter((node) => node.department !== department).map((n) => n.id),
	)
}

export function buildElkGraph(
	visibleNodes: NodeOut[],
	edges: EdgeOut[],
): ElkNode {
	const visibleIds = new Set(visibleNodes.map((n) => n.id))
	const skeletonEdges: ElkExtendedEdge[] = edges
		.filter(
			(e) =>
				e.relation === 'solid' &&
				e.is_primary &&
				visibleIds.has(e.manager_id) &&
				visibleIds.has(e.report_id),
		)
		.map((e) => ({
			id: `${e.manager_id}->${e.report_id}`,
			sources: [e.manager_id],
			targets: [e.report_id],
		}))

	return {
		id: 'root',
		layoutOptions: {
			'elk.algorithm': 'layered',
			'elk.direction': 'DOWN',
			'elk.layered.spacing.nodeNodeBetweenLayers': '64',
			'elk.spacing.nodeNode': '32',
			// The default strategy (BRANDES_KOEPF) optimizes for straight edges
			// and can leave a parent flush against one edge of its subtree
			// instead of centered over its children - confirmed by comparing
			// strategies directly against elkjs on both symmetric and
			// asymmetric fan-outs. SIMPLE centers a parent over the midpoint
			// (symmetric case) or median (odd fan-out) of its children instead.
			'elk.layered.nodePlacement.strategy': 'SIMPLE',
		},
		children: visibleNodes.map((node) => ({
			id: node.id,
			width: NODE_WIDTH,
			height: NODE_HEIGHT,
		})),
		edges: skeletonEdges,
	}
}

/** A straight anchor-to-anchor line for an overlay (non-skeleton) edge,
 * given already-computed node positions. */
export function overlayEdgePoints(
	manager: { x: number; y: number; width: number; height: number },
	report: { x: number; y: number; width: number; height: number },
): [Point, Point] {
	return [
		{ x: manager.x + manager.width / 2, y: manager.y + manager.height },
		{ x: report.x + report.width / 2, y: report.y },
	]
}

export function visibleNodesOf(
	graph: GraphOut,
	hiddenIds: ReadonlySet<string>,
): NodeOut[] {
	return graph.nodes.filter((node) => !hiddenIds.has(node.id))
}
