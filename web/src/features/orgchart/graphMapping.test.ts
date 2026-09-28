import { describe, expect, it } from 'vitest'

import type { EdgeOut, GraphOut, NodeOut } from '../../api/schemas'
import {
	buildElkGraph,
	computeDimmedIds,
	computeHiddenIds,
	computePrimaryChildren,
	computePrimaryParents,
	overlayEdgePoints,
	visibleNodesOf,
} from './graphMapping'

function node(id: string, department = 'Engineering'): NodeOut {
	return { id, title: id, department, status: 'active', occupants: null }
}

function edge(
	managerId: string,
	reportId: string,
	relation: 'solid' | 'dotted' = 'solid',
	isPrimary = true,
): EdgeOut {
	return {
		manager_id: managerId,
		report_id: reportId,
		relation,
		is_primary: isPrimary,
	}
}

// CEO -> VP -> Dir1, Dir2 (both solid primary); Dir1 also dotted-reports to VP2 (not primary).
const CEO_VP_DIR_GRAPH: { nodes: NodeOut[]; edges: EdgeOut[] } = {
	nodes: [
		node('ceo'),
		node('vp'),
		node('dir1'),
		node('dir2'),
		node('vp2', 'Sales'),
	],
	edges: [
		edge('ceo', 'vp'),
		edge('vp', 'dir1'),
		edge('vp', 'dir2'),
		edge('vp2', 'dir1', 'dotted', false),
	],
}

describe('computePrimaryParents', () => {
	it('maps each report to its primary solid manager', () => {
		const parents = computePrimaryParents(CEO_VP_DIR_GRAPH.edges)

		expect(parents.get('vp')).toBe('ceo')
		expect(parents.get('dir1')).toBe('vp')
		expect(parents.get('dir2')).toBe('vp')
	})

	it('does not include a non-primary edge as a parent', () => {
		const parents = computePrimaryParents(CEO_VP_DIR_GRAPH.edges)

		// dir1's dotted line to vp2 must not appear as a second parent entry.
		expect(parents.get('dir1')).toBe('vp')
	})
})

describe('computePrimaryChildren', () => {
	it('groups skeleton children by manager', () => {
		const children = computePrimaryChildren(CEO_VP_DIR_GRAPH.edges)

		expect(children.get('vp')).toEqual(['dir1', 'dir2'])
		expect(children.get('ceo')).toEqual(['vp'])
		expect(children.has('dir1')).toBe(false)
	})
})

describe('computeHiddenIds', () => {
	it('hides only the descendants of a collapsed node, not the node itself', () => {
		const hidden = computeHiddenIds(CEO_VP_DIR_GRAPH.edges, new Set(['vp']))

		expect(hidden.has('vp')).toBe(false)
		expect(hidden.has('dir1')).toBe(true)
		expect(hidden.has('dir2')).toBe(true)
		expect(hidden.has('ceo')).toBe(false)
	})

	it('hides nothing when nothing is collapsed', () => {
		expect(computeHiddenIds(CEO_VP_DIR_GRAPH.edges, new Set())).toEqual(
			new Set(),
		)
	})

	it('collapsing a leaf hides nothing further', () => {
		const hidden = computeHiddenIds(CEO_VP_DIR_GRAPH.edges, new Set(['dir1']))

		expect(hidden.size).toBe(0)
	})
})

describe('computeDimmedIds', () => {
	it('dims every node outside the selected department', () => {
		const dimmed = computeDimmedIds(CEO_VP_DIR_GRAPH.nodes, 'Sales')

		expect(dimmed.has('vp2')).toBe(false)
		expect(dimmed.has('ceo')).toBe(true)
		expect(dimmed.has('vp')).toBe(true)
	})

	it('dims nothing when no department is selected', () => {
		expect(computeDimmedIds(CEO_VP_DIR_GRAPH.nodes, null)).toEqual(new Set())
	})
})

describe('visibleNodesOf', () => {
	it('excludes hidden node ids', () => {
		const graph: GraphOut = { ...CEO_VP_DIR_GRAPH, root_ids: ['ceo'] }

		const visible = visibleNodesOf(graph, new Set(['dir1']))

		expect(visible.map((n) => n.id)).toEqual(['ceo', 'vp', 'dir2', 'vp2'])
	})
})

describe('buildElkGraph', () => {
	it('includes only primary solid edges between visible nodes', () => {
		const elkGraph = buildElkGraph(
			CEO_VP_DIR_GRAPH.nodes,
			CEO_VP_DIR_GRAPH.edges,
		)

		expect(elkGraph.edges).toHaveLength(3)
		expect(elkGraph.children).toHaveLength(5)
	})

	it('excludes an edge whose endpoint was filtered out as hidden', () => {
		const visibleNodes = CEO_VP_DIR_GRAPH.nodes.filter((n) => n.id !== 'dir1')

		const elkGraph = buildElkGraph(visibleNodes, CEO_VP_DIR_GRAPH.edges)

		const edgeIds = elkGraph.edges?.map((e) => e.id) ?? []
		expect(edgeIds).not.toContain('vp->dir1')
	})
})

describe('overlayEdgePoints', () => {
	it('anchors from the manager bottom-center to the report top-center', () => {
		const manager = { x: 0, y: 0, width: 200, height: 100 }
		const report = { x: 300, y: 200, width: 200, height: 100 }

		const [start, end] = overlayEdgePoints(manager, report)

		expect(start).toEqual({ x: 100, y: 100 })
		expect(end).toEqual({ x: 400, y: 200 })
	})
})
