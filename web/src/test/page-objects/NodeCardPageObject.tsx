import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'

import { NodeCard } from '../../features/orgchart/NodeCard'
import type { PositionedNode } from '../../features/orgchart/types'
import { renderWithProviders, screen } from '../render'

export class NodeCardPageObject {
	readonly onOpen = vi.fn()
	readonly onToggleCollapse = vi.fn()
	readonly onKeyDown = vi.fn()
	private readonly node: PositionedNode

	constructor(node: PositionedNode) {
		this.node = node
		renderWithProviders(
			<NodeCard
				node={node}
				onOpen={this.onOpen}
				onToggleCollapse={this.onToggleCollapse}
				onKeyDown={this.onKeyDown}
			/>,
		)
	}

	get card() {
		return screen.getByRole('button', { name: new RegExp(this.node.title) })
	}

	get toggle() {
		return screen.queryByRole('button', { name: /reports of/i })
	}

	async open() {
		await userEvent.click(this.card)
	}

	async toggleCollapsed() {
		const toggle = this.toggle
		if (!toggle) throw new Error('no collapse toggle rendered for this node')
		await userEvent.click(toggle)
	}
}
