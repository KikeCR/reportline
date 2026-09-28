import js from '@eslint/js'
import { defineConfig, globalIgnores } from 'eslint/config'
import prettierConfig from 'eslint-config-prettier'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import globals from 'globals'
import tseslint from 'typescript-eslint'

export default defineConfig([
	globalIgnores(['dist', 'coverage', 'src/api/schema.d.ts']),
	{
		files: ['**/*.{ts,tsx}'],
		extends: [
			js.configs.recommended,
			tseslint.configs.recommended,
			prettierConfig,
		],
		languageOptions: {
			ecmaVersion: 2023,
			globals: globals.browser,
		},
		rules: {
			// The Zod-vs-generated-type equality check pattern in api/schemas.ts
			// declares `type _CheckX = Expect<...>` purely for the compiler to
			// evaluate - it's never referenced by name, by design.
			'@typescript-eslint/no-unused-vars': [
				'error',
				{ varsIgnorePattern: '^_' },
			],
		},
	},
	{
		// eslint-plugin-react-hooks's `recommended-latest` preset ships in the
		// legacy eslintrc `plugins: ['react-hooks']` array shape, which flat
		// config's `extends` rejects - so its plugin/rules are wired up here
		// by hand instead of extended.
		files: ['**/*.{ts,tsx}'],
		plugins: { 'react-hooks': reactHooks },
		rules: reactHooks.configs['recommended-latest'].rules,
	},
	{
		// Fast Refresh only matters for app source loaded by the Vite dev
		// server - test helpers and test files legitimately export
		// non-component values (render wrappers, page objects, fixtures).
		files: ['src/**/*.{ts,tsx}'],
		ignores: ['**/*.test.{ts,tsx}', 'src/test/**'],
		extends: [reactRefresh.configs.vite],
	},
])
