import { useContext } from 'react'

import { OrgContext, type OrgContextValue } from './OrgContext'

export function useOrg(): OrgContextValue {
	const context = useContext(OrgContext)
	if (context === null) {
		throw new Error('useOrg must be used within an OrgProvider')
	}
	return context
}
