import '@testing-library/jest-dom/vitest'

import { afterEach } from 'vitest'

afterEach(() => {
	try {
		localStorage.clear()
	} catch {
		// ignore - not every test touches storage
	}
})
