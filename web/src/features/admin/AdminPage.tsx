import { useOrg } from '../../context/useOrg'
import { useQuarantine, useRunSync, useSyncRuns } from '../../api/queries'
import './AdminPage.css'

export function AdminPage() {
	const { orgId } = useOrg()
	const syncRuns = useSyncRuns(orgId)
	const quarantine = useQuarantine(orgId)
	const runSync = useRunSync(orgId)

	if (!orgId) {
		return <p className="admin-page__empty">Select a tenant above first.</p>
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
						{runSync.isPending ? 'Syncing…' : 'Sync workday_like'}
					</button>
					<button
						type="button"
						disabled={runSync.isPending}
						onClick={() => runSync.mutate('bamboo_like')}
					>
						{runSync.isPending ? 'Syncing…' : 'Sync bamboo_like'}
					</button>
				</div>

				<div className="admin-page__table-wrapper">
					<table className="admin-page__table">
						<thead>
							<tr>
								<th>Source</th>
								<th>Created</th>
								<th>Updated</th>
								<th>Unchanged</th>
								<th>Quarantined</th>
								<th>Duration</th>
								<th>Started</th>
							</tr>
						</thead>
						<tbody>
							{syncRuns.data?.results.length === 0 && (
								<tr>
									<td colSpan={7} className="admin-page__empty-row">
										No sync runs yet - click a button above to run one.
									</td>
								</tr>
							)}
							{syncRuns.data?.results.map((run, i) => (
								<tr key={i}>
									<td>
										<code>{run.source}</code>
									</td>
									<td>{run.created_count}</td>
									<td>{run.updated_count}</td>
									<td>{run.unchanged_count}</td>
									<td>
										<span
											className={`admin-page__badge ${
												run.quarantined_count > 0
													? 'admin-page__badge--nonzero'
													: 'admin-page__badge--zero'
											}`}
										>
											{run.quarantined_count}
										</span>
									</td>
									<td>{run.duration_ms} ms</td>
									<td>{new Date(run.started_at).toLocaleString()}</td>
								</tr>
							))}
						</tbody>
					</table>
				</div>
			</section>

			<section>
				<h2>Quarantine</h2>
				<div className="admin-page__table-wrapper">
					<table className="admin-page__table">
						<thead>
							<tr>
								<th>Source</th>
								<th>Reason</th>
								<th>Raw record</th>
								<th>Created</th>
							</tr>
						</thead>
						<tbody>
							{quarantine.data?.results.length === 0 && (
								<tr>
									<td colSpan={4} className="admin-page__empty-row">
										Nothing quarantined.
									</td>
								</tr>
							)}
							{quarantine.data?.results.map((record, i) => (
								<tr key={i}>
									<td>
										<code>{record.source}</code>
									</td>
									<td>{record.errors.join('; ')}</td>
									<td>
										<code>{JSON.stringify(record.raw)}</code>
									</td>
									<td>{new Date(record.created_at).toLocaleString()}</td>
								</tr>
							))}
						</tbody>
					</table>
				</div>
			</section>
		</div>
	)
}
