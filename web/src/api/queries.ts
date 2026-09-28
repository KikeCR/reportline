import {
	keepPreviousData,
	useMutation,
	useQuery,
	useQueryClient,
} from '@tanstack/react-query'

import {
	addReportingLine,
	getDescendants,
	getEmployee,
	getGraph,
	getPosition,
	getQuarantine,
	getSyncRuns,
	removeReportingLine,
	runSync,
} from './client'

export function useGraph(
	orgId: string,
	params: { view: 'positions' | 'people'; asOf?: string },
) {
	return useQuery({
		queryKey: ['graph', orgId, params.view, params.asOf ?? null],
		queryFn: () => getGraph(orgId, params),
		enabled: orgId.length > 0,
		// Holds the previous graph on screen (dataviz's "refetch keeps the
		// frame" rule) instead of a skeleton/blank flash when filters change.
		placeholderData: keepPreviousData,
	})
}

export function usePosition(orgId: string, positionId: string | null) {
	return useQuery({
		queryKey: ['position', orgId, positionId],
		queryFn: () => getPosition(orgId, positionId as string),
		enabled: orgId.length > 0 && positionId !== null,
	})
}

export function useDescendants(orgId: string, positionId: string | null) {
	return useQuery({
		queryKey: ['descendants', orgId, positionId],
		queryFn: () => getDescendants(orgId, positionId as string),
		enabled: orgId.length > 0 && positionId !== null,
	})
}

export function useEmployee(orgId: string, employeeId: string | null) {
	return useQuery({
		queryKey: ['employee', orgId, employeeId],
		queryFn: () => getEmployee(orgId, employeeId as string),
		enabled: orgId.length > 0 && employeeId !== null,
	})
}

export function useAddReportingLine(orgId: string) {
	const queryClient = useQueryClient()
	return useMutation({
		mutationFn: (body: {
			manager_id: string
			report_id: string
			relation: 'solid' | 'dotted'
			is_primary: boolean
		}) => addReportingLine(orgId, body),
		onSuccess: () => {
			void queryClient.invalidateQueries({ queryKey: ['graph', orgId] })
		},
	})
}

export function useRemoveReportingLine(orgId: string) {
	const queryClient = useQueryClient()
	return useMutation({
		mutationFn: (body: { manager_id: string; report_id: string }) =>
			removeReportingLine(orgId, body),
		onSuccess: () => {
			void queryClient.invalidateQueries({ queryKey: ['graph', orgId] })
		},
	})
}

export function useSyncRuns(orgId: string) {
	return useQuery({
		queryKey: ['sync-runs', orgId],
		queryFn: () => getSyncRuns(orgId),
		enabled: orgId.length > 0,
	})
}

export function useQuarantine(orgId: string) {
	return useQuery({
		queryKey: ['quarantine', orgId],
		queryFn: () => getQuarantine(orgId),
		enabled: orgId.length > 0,
	})
}

export function useRunSync(orgId: string) {
	const queryClient = useQueryClient()
	return useMutation({
		mutationFn: (source: 'workday_like' | 'bamboo_like') =>
			runSync(orgId, source),
		onSuccess: () => {
			void queryClient.invalidateQueries({ queryKey: ['sync-runs', orgId] })
			void queryClient.invalidateQueries({ queryKey: ['quarantine', orgId] })
			void queryClient.invalidateQueries({ queryKey: ['graph', orgId] })
		},
	})
}
