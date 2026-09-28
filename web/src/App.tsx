import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useEffect, useState } from 'react'

import './App.css'
import { useOrganizations } from './api/queries'
import { OrgProvider } from './context/OrgProvider'
import { useOrg } from './context/useOrg'
import { AdminPage } from './features/admin/AdminPage'
import { OrgChartPage } from './features/orgchart/OrgChartPage'

const queryClient = new QueryClient()

function OrgPicker() {
	const { orgId, setOrgId } = useOrg()
	const organizations = useOrganizations()

	// Auto-select the first tenant so the chart loads with zero clicks.
	useEffect(() => {
		if (!orgId && organizations.data && organizations.data.results.length > 0) {
			setOrgId(organizations.data.results[0]!.id)
		}
	}, [orgId, organizations.data, setOrgId])

	if (organizations.isLoading) {
		return <span className="app-header__org-field">Loading tenants…</span>
	}

	if (organizations.isError) {
		return (
			<span className="app-header__org-field" role="alert">
				Can&apos;t reach the API - is the backend running?
			</span>
		)
	}

	return (
		<label className="app-header__org-field">
			<span>Tenant</span>
			<select
				value={orgId}
				onChange={(event) => {
					setOrgId(event.target.value)
				}}
			>
				{organizations.data?.results.length === 0 && (
					<option value="">No tenants seeded yet</option>
				)}
				{organizations.data?.results.map((org) => (
					<option key={org.id} value={org.id}>
						{org.name}
					</option>
				))}
			</select>
		</label>
	)
}

function AppShell() {
	const [tab, setTab] = useState<'orgchart' | 'admin'>('orgchart')

	return (
		<div className="app-shell">
			<header className="app-header">
				<h1>Reportline</h1>
				<nav className="app-header__tabs">
					<button
						type="button"
						className={tab === 'orgchart' ? 'is-active' : ''}
						onClick={() => {
							setTab('orgchart')
						}}
					>
						Org chart
					</button>
					<button
						type="button"
						className={tab === 'admin' ? 'is-active' : ''}
						onClick={() => {
							setTab('admin')
						}}
					>
						Admin
					</button>
				</nav>
				<OrgPicker />
			</header>
			<main className="app-main">
				{tab === 'orgchart' ? <OrgChartPage /> : <AdminPage />}
			</main>
		</div>
	)
}

export default function App() {
	return (
		<QueryClientProvider client={queryClient}>
			<OrgProvider>
				<AppShell />
			</OrgProvider>
		</QueryClientProvider>
	)
}
