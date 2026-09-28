import type { EdgeOut, NodeOut } from '../../api/schemas'

export const NODE_WIDTH = 220
export const NODE_HEIGHT = 92

export interface PositionedNode extends NodeOut {
	x: number
	y: number
	width: number
	height: number
	hasChildren: boolean
	collapsed: boolean
	dimmed: boolean
}

export interface Point {
	x: number
	y: number
}

export interface PositionedEdge extends EdgeOut {
	id: string
	points: [Point, Point]
}

export interface LaidOutGraph {
	nodes: PositionedNode[]
	edges: PositionedEdge[]
	width: number
	height: number
}
