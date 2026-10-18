// e2e tests run outside Vite, so read the content config directly instead of via the $content alias.
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import type { GoluConfig } from '../../src/lib/config';

const path = fileURLToPath(new URL('../../../content/golu.config.json', import.meta.url));
export const config = JSON.parse(readFileSync(path, 'utf8')) as GoluConfig;
