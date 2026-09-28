import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useState } from 'react'

import './App.css'
import { OrgProvider } from './context/OrgProvider'
import { useOrg } from './context/useOrg'
import { AdminPage } from './features/admin/AdminPage'
import { OrgChartPage } from './features/orgchart/OrgChartPage'

const queryClient = new QueryClient()

function OrgIdField() {
	const { orgId, setOrgId } = useOrg()

	return (
		<label className="app-header__org-field">
			<span>Tenant id</span>
			<input
				type="text"
				value={orgId}
				placeholder="paste an organization id"
				onChange={(event) => {
					setOrgId(event.target.value.trim())
				}}
			/>
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
				<OrgIdField />
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
