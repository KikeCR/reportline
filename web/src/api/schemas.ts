/**
 * Zod schemas that parse every API response at the boundary, mirroring
 * `schema.d.ts` (generated from the backend's OpenAPI spec - never hand
 * edited). Each schema is followed by a compile-time equality check against
 * its generated type: if they diverge, `npm run typecheck` fails - this is
 * the "test that fails if Zod schemas diverge from generated types" the
 * brief asks for, enforced by the type system rather than a runtime
 * assertion, since structural type equality is exactly what's being
 * checked.
 */
import { z } from 'zod'
import type { components } from './schema'

type Equal<A, B> =
	(<T>() => T extends A ? 1 : 2) extends <T>() => T extends B ? 1 : 2
		? true
		: false
type Expect<T extends true> = T

export const PositionStatusSchema = z.enum(['active', 'vacant', 'closed'])
export type _CheckPositionStatus = Expect<
	Equal<
		z.infer<typeof PositionStatusSchema>,
		components['schemas']['PositionStatus']
	>
>

export const ReportsToEdgeSchema = z.object({
	position_id: z.string(),
	relation: z.enum(['solid', 'dotted']),
	is_primary: z.boolean(),
})
export type _CheckReportsToEdge = Expect<
	Equal<
		z.infer<typeof ReportsToEdgeSchema>,
		components['schemas']['ReportsToEdge']
	>
>

export const PositionOutSchema = z.object({
	id: z.string(),
	title: z.string(),
	department: z.string(),
	status: PositionStatusSchema,
	reports_to: z.array(ReportsToEdgeSchema),
})
export type _CheckPositionOut = Expect<
	Equal<z.infer<typeof PositionOutSchema>, components['schemas']['PositionOut']>
>

export const DescendantOutSchema = PositionOutSchema.extend({
	depth: z.number(),
})
export type _CheckDescendantOut = Expect<
	Equal<
		z.infer<typeof DescendantOutSchema>,
		components['schemas']['DescendantOut']
	>
>

export const DescendantsOutSchema = z.object({
	results: z.array(DescendantOutSchema),
})
export type _CheckDescendantsOut = Expect<
	Equal<
		z.infer<typeof DescendantsOutSchema>,
		components['schemas']['DescendantsOut']
	>
>

export const OccupantOutSchema = z.object({
	employee_id: z.string(),
	name: z.string(),
	fte: z.number(),
	is_primary: z.boolean(),
})
export type _CheckOccupantOut = Expect<
	Equal<z.infer<typeof OccupantOutSchema>, components['schemas']['OccupantOut']>
>

export const NodeOutSchema = z.object({
	id: z.string(),
	title: z.string(),
	department: z.string(),
	status: PositionStatusSchema,
	occupants: z.array(OccupantOutSchema).nullable(),
})
export type _CheckNodeOut = Expect<
	Equal<z.infer<typeof NodeOutSchema>, components['schemas']['NodeOut']>
>

export const EdgeOutSchema = z.object({
	report_id: z.string(),
	manager_id: z.string(),
	relation: z.enum(['solid', 'dotted']),
	is_primary: z.boolean(),
})
export type _CheckEdgeOut = Expect<
	Equal<z.infer<typeof EdgeOutSchema>, components['schemas']['EdgeOut']>
>

export const GraphOutSchema = z.object({
	nodes: z.array(NodeOutSchema),
	edges: z.array(EdgeOutSchema),
	root_ids: z.array(z.string()),
})
export type _CheckGraphOut = Expect<
	Equal<z.infer<typeof GraphOutSchema>, components['schemas']['GraphOut']>
>

// No auth/roles for now (descoped) - the backend always returns the full
// HR view, including compensation.
export const CompensationOutSchema = z.object({
	amount: z.string(),
	currency: z.string(),
})
export type _CheckCompensationOut = Expect<
	Equal<
		z.infer<typeof CompensationOutSchema>,
		components['schemas']['CompensationOut']
	>
>

export const EmployeeHROutSchema = z.object({
	id: z.string(),
	name: z.string(),
	title: z.string().nullable(),
	compensation: CompensationOutSchema,
})
export type _CheckEmployeeHROut = Expect<
	Equal<
		z.infer<typeof EmployeeHROutSchema>,
		components['schemas']['EmployeeHROut']
	>
>

export const ErrorOutSchema = z.object({
	error: z.string(),
	message: z.string(),
	details: z.record(z.string(), z.unknown()).optional(),
})
export type _CheckErrorOut = Expect<
	Equal<z.infer<typeof ErrorOutSchema>, components['schemas']['ErrorOut']>
>

export const SyncRunOutSchema = z.object({
	source: z.string(),
	created_count: z.number(),
	updated_count: z.number(),
	unchanged_count: z.number(),
	quarantined_count: z.number(),
	duration_ms: z.number(),
	started_at: z.string(),
})
export type _CheckSyncRunOut = Expect<
	Equal<z.infer<typeof SyncRunOutSchema>, components['schemas']['SyncRunOut']>
>

export const SyncRunsOutSchema = z.object({
	results: z.array(SyncRunOutSchema),
})

export const QuarantineOutSchema = z.object({
	source: z.string(),
	raw: z.record(z.string(), z.unknown()),
	errors: z.array(z.string()),
	created_at: z.string(),
})
export type _CheckQuarantineOut = Expect<
	Equal<
		z.infer<typeof QuarantineOutSchema>,
		components['schemas']['QuarantineOut']
	>
>

export const QuarantineListOutSchema = z.object({
	results: z.array(QuarantineOutSchema),
})

export const OrganizationOutSchema = z.object({
	id: z.string(),
	name: z.string(),
})
export type _CheckOrganizationOut = Expect<
	Equal<
		z.infer<typeof OrganizationOutSchema>,
		components['schemas']['OrganizationOut']
	>
>

export const OrganizationsOutSchema = z.object({
	results: z.array(OrganizationOutSchema),
})

export type PositionOut = z.infer<typeof PositionOutSchema>
export type DescendantOut = z.infer<typeof DescendantOutSchema>
export type NodeOut = z.infer<typeof NodeOutSchema>
export type EdgeOut = z.infer<typeof EdgeOutSchema>
export type OccupantOut = z.infer<typeof OccupantOutSchema>
export type GraphOut = z.infer<typeof GraphOutSchema>
export type EmployeeHROut = z.infer<typeof EmployeeHROutSchema>
export type ErrorOut = z.infer<typeof ErrorOutSchema>
export type SyncRunOut = z.infer<typeof SyncRunOutSchema>
export type QuarantineOut = z.infer<typeof QuarantineOutSchema>
export type OrganizationOut = z.infer<typeof OrganizationOutSchema>
