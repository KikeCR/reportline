import { createContext } from 'react'

export interface OrgContextValue {
	orgId: string
	setOrgId: (orgId: string) => void
}

export const OrgContext = createContext<OrgContextValue | null>(null)
