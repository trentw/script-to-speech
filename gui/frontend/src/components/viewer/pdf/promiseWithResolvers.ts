/**
 * `Promise.withResolvers` polyfill for older WebKit (< 17.4). pdf.js 5.x
 * calls it unconditionally in its modern build, and the packaged Tauri app's
 * WKWebView tracks the host macOS Safari, which can predate it. The worker
 * side runs the legacy pdf.js build, which bundles its own polyfill (see
 * pdfSetup). This module must be imported before anything that evaluates
 * pdfjs-dist.
 */

interface PromiseWithResolvers<T> {
  promise: Promise<T>;
  resolve: (value: T | PromiseLike<T>) => void;
  reject: (reason?: unknown) => void;
}

const promiseCtor = Promise as PromiseConstructor & {
  withResolvers?: <T>() => PromiseWithResolvers<T>;
};

if (typeof promiseCtor.withResolvers !== 'function') {
  promiseCtor.withResolvers = function withResolvers<T>() {
    let resolve!: (value: T | PromiseLike<T>) => void;
    let reject!: (reason?: unknown) => void;
    const promise = new Promise<T>((res, rej) => {
      resolve = res;
      reject = rej;
    });
    return { promise, resolve, reject };
  };
}

export {};
