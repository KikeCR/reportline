import { describe, expect, it } from 'vitest'

import { NodeCardPageObject } from '../../test/page-objects/NodeCardPageObject'
import type { PositionedNode } from './types'

function buildNode(overrides: Partial<PositionedNode> = {}): PositionedNode {
	return {
		id: 'pos-1',
		title: 'VP Engineering',
		department: 'Engineering',
		status: 'active',
		occupants: [
			{ employee_id: 'emp-1', name: 'Ada Lovelace', fte: 1, is_primary: true },
		],
		x: 0,
		y: 0,
		width: 220,
		height: 92,
		hasChildren: false,
		collapsed: false,
		dimmed: false,
		...overrides,
	}
}

describe('NodeCard', () => {
	it('shows the title, department, and primary occupant', () => {
		const page = new NodeCardPageObject(buildNode())

		expect(page.card).toHaveTextContent('VP Engineering')
		expect(page.card).toHaveTextContent('Engineering')
		expect(page.card).toHaveTextContent('Ada Lovelace')
	})

	it('shows a Vacant badge instead of an occupant when vacant', () => {
		const page = new NodeCardPageObject(
			buildNode({ status: 'vacant', occupants: null }),
		)

		expect(page.card).toHaveTextContent('Vacant')
		expect(page.card).not.toHaveTextContent('Ada Lovelace')
	})

	it('shows a +N suffix when a position has more than one occupant', () => {
		const page = new NodeCardPageObject(
			buildNode({
				occupants: [
					{
						employee_id: 'e1',
						name: 'Ada Lovelace',
						fte: 0.5,
						is_primary: true,
					},
					{
						employee_id: 'e2',
						name: 'Grace Hopper',
						fte: 0.5,
						is_primary: false,
					},
				],
			}),
		)

		expect(page.card).toHaveTextContent('Ada Lovelace +1')
	})

	it('calls onOpen with the node id when clicked', async () => {
		const page = new NodeCardPageObject(buildNode({ id: 'pos-42' }))

		await page.open()

		expect(page.onOpen).toHaveBeenCalledWith('pos-42')
	})

	it('renders no collapse toggle when the node has no children', () => {
		const page = new NodeCardPageObject(buildNode({ hasChildren: false }))

		expect(page.toggle).toBeNull()
	})

	it('calls onToggleCollapse without also opening the drawer', async () => {
		const page = new NodeCardPageObject(buildNode({ hasChildren: true }))

		await page.toggleCollapsed()

		expect(page.onToggleCollapse).toHaveBeenCalledWith('pos-1')
		expect(page.onOpen).not.toHaveBeenCalled()
	})

	it('labels the toggle as expand when collapsed and collapse when expanded', () => {
		const collapsed = new NodeCardPageObject(
			buildNode({ hasChildren: true, collapsed: true }),
		)
		expect(collapsed.toggle).toHaveAccessibleName(/expand/i)
	})
})
