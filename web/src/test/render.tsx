import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, type RenderOptions } from '@testing-library/react'
import type { ReactElement, ReactNode } from 'react'

import { OrgProvider } from '../context/OrgProvider'

function AllProviders({ children }: { children: ReactNode }) {
	const queryClient = new QueryClient({
		defaultOptions: { queries: { retry: false } },
	})
	return (
		<QueryClientProvider client={queryClient}>
			<OrgProvider>{children}</OrgProvider>
		</QueryClientProvider>
	)
}

export function renderWithProviders(
	ui: ReactElement,
	options?: Omit<RenderOptions, 'wrapper'>,
) {
	return render(ui, { wrapper: AllProviders, ...options })
}

export * from '@testing-library/react'
