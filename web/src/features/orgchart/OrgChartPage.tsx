import { useEffect, useMemo, useRef, useState } from 'react'

import { useGraph } from '../../api/queries'
import { useOrg } from '../../context/useOrg'
import { DetailDrawer } from './DetailDrawer'
import { FilterBar } from './FilterBar'
import { computeDepartmentFilterHiddenIds } from './graphMapping'
import { OrgChart } from './OrgChart'
import './OrgChartPage.css'
import { useGraphLayout } from './useGraphLayout'

function today(): string {
	return new Date().toISOString().slice(0, 10)
}

export function OrgChartPage() {
	const { orgId } = useOrg()
	const [view, setView] = useState<'positions' | 'people'>('positions')
	const [department, setDepartment] = useState<string | null>(null)
	const [asOf, setAsOf] = useState(today)
	const [collapsedIds, setCollapsedIds] = useState<ReadonlySet<string>>(
		() => new Set(),
	)
	const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
	const canvasRef = useRef<HTMLDivElement>(null)

	const isToday = asOf === today()
	const graphQuery = useGraph(orgId, {
		view,
		asOf: isToday ? undefined : asOf,
	})

	const departmentHiddenIds = useMemo(
		() =>
			computeDepartmentFilterHiddenIds(
				graphQuery.data?.nodes ?? [],
				department,
			),
		[graphQuery.data, department],
	)

	const layout = useGraphLayout(
		graphQuery.data,
		collapsedIds,
		departmentHiddenIds,
	)

	// `margin: auto` on the chart centers it when it fits the canvas, but a
	// tree wider than the viewport (common - even a single department can
	// spread past 2000px) needs its scroll position centered too, or the
	// canvas just shows the left-anchored slice.
	useEffect(() => {
		const canvas = canvasRef.current
		if (!canvas || !layout) return
		canvas.scrollLeft = Math.max(
			0,
			(canvas.scrollWidth - canvas.clientWidth) / 2,
		)
	}, [layout])

	const departments = useMemo(() => {
		const set = new Set((graphQuery.data?.nodes ?? []).map((n) => n.department))
		return Array.from(set).sort()
	}, [graphQuery.data])

	function toggleCollapse(nodeId: string): void {
		setCollapsedIds((current) => {
			const next = new Set(current)
			if (next.has(nodeId)) {
				next.delete(nodeId)
			} else {
				next.add(nodeId)
			}
			return next
		})
	}

	const selectedNode = graphQuery.data?.nodes.find(
		(n) => n.id === selectedNodeId,
	)

	if (!orgId) {
		return (
			<p className="org-chart-page__empty">
				Enter a tenant id above to load its org chart.
			</p>
		)
	}

	return (
		<div className="org-chart-page">
			<FilterBar
				view={view}
				onViewChange={setView}
				department={department}
				onDepartmentChange={setDepartment}
				departments={departments}
				asOf={asOf}
				onAsOfChange={setAsOf}
			/>

			<div className="org-chart-page__canvas" ref={canvasRef}>
				{graphQuery.isLoading && (
					<p className="org-chart-page__status">Loading…</p>
				)}
				{graphQuery.isError && (
					<p className="org-chart-page__status" role="alert">
						Couldn&apos;t load the org chart: {graphQuery.error.message}
					</p>
				)}
				{layout && (
					<div
						className="org-chart-page__scroll"
						style={{ opacity: graphQuery.isFetching ? 0.6 : 1 }}
					>
						<OrgChart
							layout={layout}
							onNodeOpen={setSelectedNodeId}
							onToggleCollapse={toggleCollapse}
						/>
					</div>
				)}
			</div>

			{selectedNode && graphQuery.data && (
				<DetailDrawer
					node={selectedNode}
					nodes={graphQuery.data.nodes}
					edges={graphQuery.data.edges}
					onClose={() => {
						setSelectedNodeId(null)
					}}
				/>
			)}
		</div>
	)
}
