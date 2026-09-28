import { useEffect, useRef } from 'react'

import type { EdgeOut, NodeOut } from '../../api/schemas'
import './DetailDrawer.css'

interface DetailDrawerProps {
	node: NodeOut
	nodes: NodeOut[]
	edges: EdgeOut[]
	onClose: () => void
}

export function DetailDrawer({
	node,
	nodes,
	edges,
	onClose,
}: DetailDrawerProps) {
	const titleById = new Map(nodes.map((n) => [n.id, n.title]))
	const closeButtonRef = useRef<HTMLButtonElement>(null)

	useEffect(() => {
		closeButtonRef.current?.focus()

		function handleKeyDown(event: KeyboardEvent): void {
			if (event.key === 'Escape') {
				onClose()
			}
		}
		document.addEventListener('keydown', handleKeyDown)
		return () => {
			document.removeEventListener('keydown', handleKeyDown)
		}
	}, [onClose])

	const reportsTo = edges.filter((e) => e.report_id === node.id)
	const directReportCount = edges.filter((e) => e.manager_id === node.id).length

	return (
		<>
			<div className="detail-drawer__backdrop" onClick={onClose} />
			<aside
				className="detail-drawer"
				role="dialog"
				aria-modal="true"
				aria-labelledby="detail-drawer-title"
			>
				<div className="detail-drawer__header">
					<h2 id="detail-drawer-title">{node.title}</h2>
					<button
						ref={closeButtonRef}
						type="button"
						className="detail-drawer__close"
						onClick={onClose}
						aria-label="Close details"
					>
						×
					</button>
				</div>

				<dl className="detail-drawer__facts">
					<dt>Department</dt>
					<dd>{node.department}</dd>

					<dt>Status</dt>
					<dd>{node.status}</dd>

					<dt>Direct reports</dt>
					<dd>{directReportCount}</dd>
				</dl>

				<section>
					<h3>
						Occupant{node.occupants && node.occupants.length > 1 ? 's' : ''}
					</h3>
					{node.occupants && node.occupants.length > 0 ? (
						<ul className="detail-drawer__list">
							{node.occupants.map((occupant) => (
								<li key={occupant.employee_id}>
									{occupant.name}
									{occupant.fte < 1
										? ` (${Math.round(occupant.fte * 100)}% FTE)`
										: ''}
									{occupant.is_primary ? '' : ' · secondary'}
								</li>
							))}
						</ul>
					) : (
						<p className="detail-drawer__empty">Vacant</p>
					)}
				</section>

				<section>
					<h3>Reports to</h3>
					{reportsTo.length > 0 ? (
						<ul className="detail-drawer__list">
							{reportsTo.map((edge) => (
								<li key={`${edge.manager_id}-${edge.relation}`}>
									{titleById.get(edge.manager_id) ?? edge.manager_id}
									{' · '}
									{edge.relation}
									{edge.is_primary ? ' · primary' : ''}
								</li>
							))}
						</ul>
					) : (
						<p className="detail-drawer__empty">No manager (root position)</p>
					)}
				</section>
			</aside>
		</>
	)
}
