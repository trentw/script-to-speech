/**
 * pdf.js worker wiring for react-pdf.
 *
 * The worker is bundled locally via Vite's `?url` import (emitted as a static
 * asset), so it loads fully offline — required for the packaged Tauri app,
 * which has no network access. The *legacy* worker build is used because it
 * bundles its own polyfills (notably `Promise.withResolvers`), keeping the
 * PDF lens alive on the older WKWebViews the app's macOS floor allows; the
 * main thread gets the same guarantee from the polyfill import below, which
 * must run before react-pdf evaluates pdfjs-dist.
 *
 * Importing this module once (from PdfLens) configures the global worker;
 * keep it in its own module so tests can mock it without pulling the worker
 * asset into jsdom.
 */
import './promiseWithResolvers';

import workerUrl from 'pdfjs-dist/legacy/build/pdf.worker.min.mjs?url';
import { pdfjs } from 'react-pdf';

pdfjs.GlobalWorkerOptions.workerSrc = workerUrl;
