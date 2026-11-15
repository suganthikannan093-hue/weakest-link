import { defineConfig } from 'vite';

// Static site: everything (engine, graph, queries) runs in the browser.
// base './' keeps asset URLs relative so the build works on GitHub Pages
// (https://<user>.github.io/weakest-link/) or any static host without changes.
export default defineConfig({
  root: 'web',
  base: './',
  publicDir: 'public',
  build: { outDir: '../dist', emptyOutDir: true, target: 'es2022' },
  server: { fs: { allow: ['..'] } },
  preview: { port: 4173, strictPort: true },
});
