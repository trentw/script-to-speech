/// <reference types="vitest" />
import { defineConfig, mergeConfig } from 'vite';

import viteConfig from './vite.config';

export default defineConfig(({ mode }) => {
  // Get the base vite config by calling it with the mode
  const baseConfig =
    typeof viteConfig === 'function' ? viteConfig({ mode }) : viteConfig;

  // Define vitest-specific config
  const vitestConfig = defineConfig({
    test: {
      environment: 'jsdom',
      globals: true,
      setupFiles: './src/test/setup.ts',
      pool: 'forks', // Better isolation for Zustand stores
      exclude: ['**/node_modules/**', '**/docs/**', '**/*.spec.ts', '**/*.spec.tsx'],
      coverage: {
        provider: 'v8',
        reporter: ['text', 'json', 'html'],
        exclude: [
          'node_modules/',
          'src/test/',
          '**/*.d.ts',
          '**/*.config.*',
          '**/mockServiceWorker.js',
          '**/*.spec.tsx',
          '**/*.spec.ts',
          '**/*.test.tsx',
          '**/*.test.ts',
        ],
        thresholds: {
          lines: 80,
          functions: 80,
          branches: 80,
          statements: 80,
        },
      },
    },
  });

  // Merge the configs - baseConfig already includes all necessary plugins and resolve aliases
  return mergeConfig(baseConfig, vitestConfig);
});
