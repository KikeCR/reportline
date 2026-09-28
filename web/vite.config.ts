import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// https://vite.dev/config/
export default defineConfig({
	plugins: [react()],
	server: {
		proxy: {
			'/api/v1': 'http://127.0.0.1:5001',
			'/healthz': 'http://127.0.0.1:5001',
			'/readyz': 'http://127.0.0.1:5001',
		},
	},
	test: {
		environment: 'jsdom',
		globals: true,
		setupFiles: './src/test/setup.ts',
		coverage: {
			provider: 'v8',
			exclude: [
				'src/main.tsx',
				'src/vite-env.d.ts',
				'src/test/**',
				'src/api/schema.d.ts',
				'**/*.config.*',
			],
			thresholds: {
				lines: 80,
				statements: 80,
				functions: 80,
				branches: 75,
			},
		},
	},
})
