import { copyFile, mkdir } from 'node:fs/promises';
import { build } from 'esbuild';

await mkdir('dist', { recursive: true });
await copyFile('src/index.html', 'dist/index.html');
await copyFile('node_modules/@evenrealities/even_hub_sdk/LICENSE', 'dist/SDK-LICENSE.txt');
await build({ entryPoints: ['src/main.js'], outfile: 'dist/guide-bundle.js', bundle: true, minify: true, format: 'esm', target: 'es2020' });
