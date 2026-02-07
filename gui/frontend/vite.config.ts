import tailwindcss from '@tailwindcss/vite';
import { TanStackRouterVite } from '@tanstack/router-plugin/vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import { visualizer } from 'rollup-plugin-visualizer';
import { fileURLToPath } from 'url';
import { defineConfig } from 'vite';

import pkg from './package.json';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const isAnalyze = mode === 'analyze';

  return {
    define: {
      __APP_VERSION__: JSON.stringify(pkg.version),
    },
    plugins: [
      tailwindcss(),
      TanStackRouterVite({
        autoCodeSplitting: true,
        generatedRouteTree: './src/routeTree.gen.ts',
      }),
      react(),
      // Bundle analyzer plugin - only enabled in analyze mode
      isAnalyze &&
        visualizer({
          filename: './dist/stats.html',
          open: true,
          gzipSize: true,
          brotliSize: true,
          template: 'treemap', // or 'sunburst', 'network', 'raw-data'
        }),
    ].filter(Boolean),
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    css: {
      devSourcemap: true,
    },
    server: {
      hmr: {
        overlay: true,
      },
      proxy: {
        // Proxy API requests to backend server
        '/api': {
          target: 'http://127.0.0.1:8000',
          changeOrigin: true,
          secure: false,
        },
      },
    },
    build: {
      // Performance budgets
      chunkSizeWarningLimit: 50, // 50KB per chunk warning
      rollupOptions: {
        output: {
          manualChunks: {
            // Group vendor chunks to optimize caching
            'react-vendor': ['react', 'react-dom'],
            'ui-vendor': [
              '@radix-ui/react-dialog',
              '@radix-ui/react-select',
              '@radix-ui/react-tabs',
            ],
            'query-vendor': ['@tanstack/react-query'],
          },
        },
      },
      // Target modern browsers for smaller bundles
      target: 'es2020',
      // Enable minification
      minify: 'terser',
      // Report compressed size
      reportCompressedSize: true,
    },
  };
});
