// @ts-check
import { defineConfig } from 'astro/config';

// Once the repo is pushed as <username>.github.io, this is the public URL.
// With a custom domain later, change `site` and add public/CNAME.
export default defineConfig({
  site: 'https://eseiler18.github.io',
  trailingSlash: 'ignore',
});
