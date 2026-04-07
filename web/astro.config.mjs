// @ts-check

import mdx from '@astrojs/mdx';
import sitemap from '@astrojs/sitemap';
import { defineConfig } from 'astro/config';

// https://astro.build/config
export default defineConfig({
	site: 'https://jighog1.github.io',
	base: '/my-auto-blog',
	integrations: [mdx(), sitemap()],
});
