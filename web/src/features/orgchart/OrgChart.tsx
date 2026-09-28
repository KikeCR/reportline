import { useRef } from 'react'

import { NodeCard } from './NodeCard'
import type { LaidOutGraph, PositionedNode } from './types'
import './OrgChart.css'

interface OrgChartProps {
	layout: LaidOutGraph
	onNodeOpen: (nodeId: string) => void
	onToggleCollapse: (nodeId: string) => void
}

const ARROW_DIRECTIONS: Record<string, [number, number]> = {
	ArrowUp: [0, -1],
	ArrowDown: [0, 1],
	ArrowLeft: [-1, 0],
	ArrowRight: [1, 0],
}

/** Moves focus to the nearest node in the arrow's direction, so keyboard
 * users can traverse the chart spatially, not just in DOM/tab order. */
function findNodeInDirection(
	nodes: PositionedNode[],
	from: PositionedNode,
	dx: number,
	dy: number,
): PositionedNode | null {
	let best: PositionedNode | null = null
	let bestScore = Number.POSITIVE_INFINITY

	for (const candidate of nodes) {
		if (candidate.id === from.id) continue
		const deltaX = candidate.x - from.x
		const deltaY = candidate.y - from.y
		if (dx !== 0 && (Math.sign(deltaX) !== dx || deltaX === 0)) continue
		if (dy !== 0 && (Math.sign(deltaY) !== dy || deltaY === 0)) continue

		const along = dx !== 0 ? Math.abs(deltaX) : Math.abs(deltaY)
		const across = dx !== 0 ? Math.abs(deltaY) : Math.abs(deltaX)
		const score = along + across * 2
		if (score < bestScore) {
			bestScore = score
			best = candidate
		}
	}
	return best
}

export function OrgChart({
	layout,
	onNodeOpen,
	onToggleCollapse,
}: OrgChartProps) {
	const nodeRefs = useRef(new Map<string, HTMLButtonElement>())

	function handleKeyDown(event: React.KeyboardEvent, nodeId: string): void {
		const direction = ARROW_DIRECTIONS[event.key]
		if (!direction) return
		const current = layout.nodes.find((n) => n.id === nodeId)
		if (!current) return

		event.preventDefault()
		const [dx, dy] = direction
		const next = findNodeInDirection(layout.nodes, current, dx, dy)
		if (next) {
			nodeRefs.current.get(next.id)?.focus()
		}
	}

	return (
		<div
			className="org-chart"
			style={{ width: layout.width, height: layout.height }}
			role="group"
			aria-label="Org chart"
		>
			<svg
				className="org-chart__edges"
				width={layout.width}
				height={layout.height}
				aria-hidden="true"
			>
				{layout.edges.map((edge) => {
					const [start, end] = edge.points
					const classNames = [
						'org-chart__edge',
						`org-chart__edge--${edge.relation}`,
						edge.is_primary ? 'org-chart__edge--primary' : '',
					]
						.filter(Boolean)
						.join(' ')
					return (
						<line
							key={edge.id}
							x1={start.x}
							y1={start.y}
							x2={end.x}
							y2={end.y}
							className={classNames}
						/>
					)
				})}
			</svg>
			{layout.nodes.map((node) => (
				<NodeCard
					key={node.id}
					node={node}
					onOpen={onNodeOpen}
					onToggleCollapse={onToggleCollapse}
					onKeyDown={handleKeyDown}
					ref={(element) => {
						if (element) {
							nodeRefs.current.set(node.id, element)
						} else {
							nodeRefs.current.delete(node.id)
						}
					}}
				/>
			))}
		</div>
	)
}
