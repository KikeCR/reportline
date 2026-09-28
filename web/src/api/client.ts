/**
 * A typed fetch wrapper. Every response is parsed with a Zod schema at the
 * boundary before the rest of the app ever sees it - a malformed or
 * unexpectedly-shaped response fails loudly here, not deep inside a
 * component.
 */
import { z } from 'zod'

import {
	DescendantsOutSchema,
	EmployeeHROutSchema,
	ErrorOutSchema,
	GraphOutSchema,
	PositionOutSchema,
	QuarantineListOutSchema,
	SyncRunOutSchema,
	SyncRunsOutSchema,
	type ErrorOut,
} from './schemas'

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api/v1'

export class ApiError extends Error {
	readonly status: number
	readonly body: ErrorOut

	constructor(status: number, body: ErrorOut) {
		super(body.message)
		this.status = status
		this.body = body
	}
}

async function request<T>(
	orgId: string,
	path: string,
	schema: z.ZodType<T>,
	init?: RequestInit,
): Promise<T> {
	const response = await fetch(`${BASE_URL}${path}`, {
		...init,
		headers: {
			'X-Org-Id': orgId,
			'Content-Type': 'application/json',
			...init?.headers,
		},
	})
	const json: unknown = await response.json()

	if (!response.ok) {
		throw new ApiError(response.status, ErrorOutSchema.parse(json))
	}
	return schema.parse(json)
}

export function getGraph(
	orgId: string,
	params: { view?: 'positions' | 'people'; asOf?: string } = {},
) {
	const query = new URLSearchParams()
	if (params.view) query.set('view', params.view)
	if (params.asOf) query.set('as_of', params.asOf)
	const suffix = query.size > 0 ? `?${query.toString()}` : ''
	return request(orgId, `/org/graph${suffix}`, GraphOutSchema)
}

export function getPosition(orgId: string, positionId: string) {
	return request(orgId, `/org/positions/${positionId}`, PositionOutSchema)
}

export function getDescendants(orgId: string, positionId: string) {
	return request(
		orgId,
		`/org/positions/${positionId}/descendants`,
		DescendantsOutSchema,
	)
}

export function getEmployee(orgId: string, employeeId: string) {
	return request(orgId, `/employees/${employeeId}`, EmployeeHROutSchema)
}

export function addReportingLine(
	orgId: string,
	body: {
		manager_id: string
		report_id: string
		relation: 'solid' | 'dotted'
		is_primary: boolean
	},
) {
	return request(orgId, '/org/reporting-lines', PositionOutSchema, {
		method: 'POST',
		body: JSON.stringify(body),
	})
}

export function removeReportingLine(
	orgId: string,
	body: { manager_id: string; report_id: string },
) {
	return request(orgId, '/org/reporting-lines', PositionOutSchema, {
		method: 'DELETE',
		body: JSON.stringify(body),
	})
}

export function runSync(orgId: string, source: 'workday_like' | 'bamboo_like') {
	return request(orgId, `/admin/sync/${source}`, SyncRunOutSchema, {
		method: 'POST',
	})
}

export function getSyncRuns(orgId: string) {
	return request(orgId, '/admin/sync/runs', SyncRunsOutSchema)
}

export function getQuarantine(orgId: string) {
	return request(orgId, '/admin/quarantine', QuarantineListOutSchema)
}
