#!/usr/bin/env node
// Compiles every Excalidraw scene in website/static/diagrams/<name>.excalidraw
// to website/static/img/diagrams/<name>.svg with Excalidraw's own exporter.
//
// The exporter runs inside a headless Chromium driven by Playwright, and the
// scene's fonts are embedded in each SVG, so the SVG renders with no network.
// Every request the page makes outside a local server on 127.0.0.1 is aborted.
// Scenes are drawn in ink on white with one pastel tint; the maintainer
// standard is section 8 of .claude/skills/docs-site/SKILL.md. This script is
// not part of the site bundle.
//
// The dependencies live outside website/ so the site's lock file stays as it is.
// Install them once into any folder, exact versions:
//
//   npm install --prefix <deps> --save-exact @excalidraw/excalidraw@0.18.1 \
//     react@19.3.1 react-dom@19.3.1 esbuild@0.28.2
//
// Playwright and its Chromium go into the same folder; the script loads
// Playwright from <deps> only, never from a global install:
//
//   npm install --prefix <deps> --save-exact playwright@1.63.0
//   npx --prefix <deps> playwright install chromium
//
// Then, from the repository root:
//
//   node website/scripts/build-diagrams.mjs --deps <deps>
//
// EXCALIDRAW_DEPS=<deps> works in place of --deps.

import {mkdtempSync, readFileSync, readdirSync, rmSync, writeFileSync, mkdirSync, existsSync} from 'node:fs';
import {createServer} from 'node:http';
import {createRequire} from 'node:module';
import {tmpdir} from 'node:os';
import {dirname, extname, join, resolve, sep} from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
export const websiteRoot = resolve(here, '..');
export const sourceDir = join(websiteRoot, 'static', 'diagrams');
export const outputDir = join(websiteRoot, 'static', 'img', 'diagrams');

const TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json',
  '.woff2': 'font/woff2',
  '.wasm': 'application/wasm',
};

function depsFolder(argv) {
  const i = argv.indexOf('--deps');
  const value = i >= 0 ? argv[i + 1] : process.env.EXCALIDRAW_DEPS;
  if (!value) {
    throw new Error('Name the dependency folder with --deps <folder> or EXCALIDRAW_DEPS; see the header of this script.');
  }
  return resolve(value);
}

function loadPlaywright(requireFromDeps) {
  try {
    return requireFromDeps('playwright');
  } catch {
    throw new Error('Playwright is not in the dependency folder; install playwright@1.63.0 there, as the header of this script shows.');
  }
}

function serveFile(res, root, relative) {
  const file = resolve(root, relative);
  if (!file.startsWith(root + sep) || !existsSync(file)) {
    res.writeHead(404).end();
    return;
  }
  res.writeHead(200, {'Content-Type': TYPES[extname(file)] ?? 'application/octet-stream'});
  res.end(readFileSync(file));
}

/**
 * Opens a headless page that has Excalidraw loaded as window.ExcalidrawLib,
 * runs fn(page), then closes everything.
 */
export async function withExcalidraw(deps, fn) {
  const requireFromDeps = createRequire(join(deps, 'package.json'));
  const esbuild = requireFromDeps('esbuild');
  const {chromium} = loadPlaywright(requireFromDeps);
  const assets = join(deps, 'node_modules', '@excalidraw', 'excalidraw', 'dist', 'prod');
  const bundle = mkdtempSync(join(tmpdir(), 'excalidraw-bundle-'));

  await esbuild.build({
    stdin: {
      contents: "import * as lib from '@excalidraw/excalidraw'; window.ExcalidrawLib = lib;",
      resolveDir: deps,
      loader: 'js',
    },
    bundle: true,
    format: 'esm',
    splitting: true,
    outdir: bundle,
    entryNames: 'entry',
    define: {'process.env.NODE_ENV': '"production"', 'process.env.IS_PREACT': '"false"'},
    loader: {'.css': 'empty'},
    logLevel: 'error',
  });

  const server = createServer((req, res) => {
    const path = decodeURIComponent(new URL(req.url, 'http://127.0.0.1').pathname);
    if (path === '/') {
      res.writeHead(200, {'Content-Type': TYPES['.html']});
      res.end(
        '<!doctype html><meta charset="utf-8"><title>export</title>' +
          '<script>window.EXCALIDRAW_ASSET_PATH = location.origin + "/assets/";</script>' +
          '<script type="module" src="/bundle/entry.js"></script>',
      );
    } else if (path.startsWith('/bundle/')) {
      serveFile(res, bundle, path.slice('/bundle/'.length));
    } else if (path.startsWith('/assets/')) {
      serveFile(res, assets, path.slice('/assets/'.length));
    } else {
      res.writeHead(404).end();
    }
  });
  await new Promise((done) => server.listen(0, '127.0.0.1', done));
  const origin = `http://127.0.0.1:${server.address().port}`;

  const browser = await chromium.launch();
  const blocked = [];
  try {
    const page = await browser.newPage();
    await page.route('**/*', (route) => {
      const url = route.request().url();
      if (url.startsWith(origin + '/') || url.startsWith('data:') || url.startsWith('blob:')) {
        return route.continue();
      }
      blocked.push(url);
      return route.abort();
    });
    page.on('pageerror', (error) => console.error(`page error: ${error.message}`));
    await page.goto(origin + '/');
    await page.waitForFunction(() => Boolean(window.ExcalidrawLib), null, {timeout: 60000});
    return await fn(page);
  } finally {
    await browser.close();
    server.close();
    rmSync(bundle, {recursive: true, force: true});
    if (blocked.length > 0) {
      console.error(`blocked ${blocked.length} outside request(s): ${blocked.join(', ')}`);
      process.exitCode = 1;
    }
  }
}

/** Exports one scene (the parsed .excalidraw JSON) to SVG markup. */
export async function exportScene(page, scene) {
  return page.evaluate(async (data) => {
    const lib = window.ExcalidrawLib;
    const {elements, appState, files} = lib.restore(data, null, null);
    const svg = await lib.exportToSvg({
      elements,
      appState: {...appState, exportBackground: true, exportWithDarkMode: false, exportEmbedScene: false},
      files,
      exportPadding: 24,
    });
    return svg.outerHTML;
  }, scene);
}

async function main() {
  const deps = depsFolder(process.argv.slice(2));
  const names = readdirSync(sourceDir).filter((name) => name.endsWith('.excalidraw')).sort();
  if (names.length === 0) {
    console.log(`no .excalidraw files in ${sourceDir}`);
    return;
  }
  mkdirSync(outputDir, {recursive: true});
  await withExcalidraw(deps, async (page) => {
    for (const name of names) {
      const scene = JSON.parse(readFileSync(join(sourceDir, name), 'utf-8'));
      const svg = await exportScene(page, scene);
      const out = join(outputDir, name.replace(/\.excalidraw$/, '.svg'));
      writeFileSync(out, svg + '\n', 'utf-8');
      console.log(`wrote ${out.slice(websiteRoot.length + 1)} (${Buffer.byteLength(svg)} bytes)`);
    }
  });
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch((error) => {
    console.error(error);
    process.exit(1);
  });
}
