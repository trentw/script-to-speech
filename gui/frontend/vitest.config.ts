/// <reference types="vitest" />
import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import { fileURLToPath } from 'url';
import { defineConfig, mergeConfig } from 'vite';

import viteConfig from './vite.config';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export default mergeConfig(
  viteConfig,
  defineConfig({
    plugins: [tailwindcss(), react()],
    test: {
      environment: 'jsdom',
      globals: true,
      setupFiles: './src/test/setup.ts',
      pool: 'forks', // Better isolation for Zustand stores
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
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
  })
);
