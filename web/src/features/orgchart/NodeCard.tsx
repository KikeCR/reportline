import { forwardRef } from 'react'

import type { PositionedNode } from './types'
import './NodeCard.css'

const DEPARTMENT_VAR: Record<string, string> = {
	Engineering: '--dept-engineering',
	Sales: '--dept-sales',
	Marketing: '--dept-marketing',
	Finance: '--dept-finance',
	People: '--dept-people',
	Executive: '--dept-executive',
}

function departmentColorVar(department: string): string {
	return `var(${DEPARTMENT_VAR[department] ?? '--text-muted'})`
}

interface NodeCardProps {
	node: PositionedNode
	onOpen: (nodeId: string) => void
	onToggleCollapse: (nodeId: string) => void
	onKeyDown: (event: React.KeyboardEvent, nodeId: string) => void
}

export const NodeCard = forwardRef<HTMLButtonElement, NodeCardProps>(
	function NodeCard({ node, onOpen, onToggleCollapse, onKeyDown }, ref) {
		const isVacant = node.status === 'vacant'
		const primaryOccupant =
			node.occupants?.find((o) => o.is_primary) ?? node.occupants?.[0] ?? null

		return (
			<div
				className="node-card-wrapper"
				style={{
					left: node.x,
					top: node.y,
					width: node.width,
					height: node.height,
				}}
				data-testid="node-card"
			>
				<button
					ref={ref}
					type="button"
					className={`node-card${isVacant ? ' node-card--vacant' : ''}`}
					style={{ borderLeftColor: departmentColorVar(node.department) }}
					onClick={() => {
						onOpen(node.id)
					}}
					onKeyDown={(event) => {
						onKeyDown(event, node.id)
					}}
					aria-haspopup="dialog"
					aria-label={`${node.title}, ${node.department}${isVacant ? ', vacant' : ''}`}
				>
					<span className="node-card__title">{node.title}</span>
					<span className="node-card__department">{node.department}</span>
					{isVacant ? (
						<span className="node-card__badge">Vacant</span>
					) : (
						<span className="node-card__occupant">
							{primaryOccupant?.name ?? '—'}
							{node.occupants && node.occupants.length > 1
								? ` +${node.occupants.length - 1}`
								: ''}
						</span>
					)}
				</button>
				{node.hasChildren && (
					<button
						type="button"
						className="node-card__toggle"
						onClick={(event) => {
							event.stopPropagation()
							onToggleCollapse(node.id)
						}}
						aria-label={
							node.collapsed
								? `Expand reports of ${node.title}`
								: `Collapse reports of ${node.title}`
						}
						aria-expanded={!node.collapsed}
					>
						{node.collapsed ? '+' : '−'}
					</button>
				)}
			</div>
		)
	},
)
