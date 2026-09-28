import { useOrg } from '../../context/useOrg'
import { useQuarantine, useRunSync, useSyncRuns } from '../../api/queries'
import './AdminPage.css'

export function AdminPage() {
	const { orgId } = useOrg()
	const syncRuns = useSyncRuns(orgId)
	const quarantine = useQuarantine(orgId)
	const runSync = useRunSync(orgId)

	if (!orgId) {
		return <p className="admin-page__empty">Enter a tenant id above first.</p>
	}

	return (
		<div className="admin-page">
			<section>
				<h2>HRIS sync</h2>
				<div className="admin-page__actions">
					<button
						type="button"
						disabled={runSync.isPending}
						onClick={() => runSync.mutate('workday_like')}
					>
						Sync workday_like
					</button>
					<button
						type="button"
						disabled={runSync.isPending}
						onClick={() => runSync.mutate('bamboo_like')}
					>
						Sync bamboo_like
					</button>
				</div>

				<table className="admin-page__table">
					<thead>
						<tr>
							<th>Source</th>
							<th>Created</th>
							<th>Updated</th>
							<th>Unchanged</th>
							<th>Quarantined</th>
							<th>Duration (ms)</th>
							<th>Started</th>
						</tr>
					</thead>
					<tbody>
						{syncRuns.data?.results.map((run, i) => (
							<tr key={i}>
								<td>{run.source}</td>
								<td>{run.created_count}</td>
								<td>{run.updated_count}</td>
								<td>{run.unchanged_count}</td>
								<td>{run.quarantined_count}</td>
								<td>{run.duration_ms}</td>
								<td>{new Date(run.started_at).toLocaleString()}</td>
							</tr>
						))}
					</tbody>
				</table>
			</section>

			<section>
				<h2>Quarantine</h2>
				<table className="admin-page__table">
					<thead>
						<tr>
							<th>Source</th>
							<th>Errors</th>
							<th>Raw</th>
							<th>Created</th>
						</tr>
					</thead>
					<tbody>
						{quarantine.data?.results.map((record, i) => (
							<tr key={i}>
								<td>{record.source}</td>
								<td>{record.errors.join('; ')}</td>
								<td>
									<code>{JSON.stringify(record.raw)}</code>
								</td>
								<td>{new Date(record.created_at).toLocaleString()}</td>
							</tr>
						))}
					</tbody>
				</table>
			</section>
		</div>
	)
}
