/**
 * Interim tenant selection (mirrors the backend's `X-Org-Id` placeholder -
 * see api/docs/adr/0002-api-contract.md). Phase 4 replaces this with a real
 * login that puts `org_id` in a JWT; every consumer reads `orgId` via
 * `useOrg` (./useOrg.ts), so that swap doesn't touch feature code.
 */
import { useEffect, useState, type ReactNode } from 'react'

import { OrgContext } from './OrgContext'

const STORAGE_KEY = 'reportline.orgId'

function readStoredOrgId(): string {
	try {
		return localStorage.getItem(STORAGE_KEY) ?? ''
	} catch {
		return ''
	}
}

export function OrgProvider({ children }: { children: ReactNode }) {
	const [orgId, setOrgId] = useState(readStoredOrgId)

	useEffect(() => {
		try {
			if (orgId) {
				localStorage.setItem(STORAGE_KEY, orgId)
			} else {
				localStorage.removeItem(STORAGE_KEY)
			}
		} catch {
			// Storage can be unavailable (private browsing); the org id still
			// works for the current session via React state.
		}
	}, [orgId])

	return (
		<OrgContext.Provider value={{ orgId, setOrgId }}>
			{children}
		</OrgContext.Provider>
	)
}
