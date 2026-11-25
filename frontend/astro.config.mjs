// @ts-check
import { defineConfig } from 'astro/config';

import cloudflare from '@astrojs/cloudflare';
import tailwindcss from '@tailwindcss/vite';

import sitemap from '@astrojs/sitemap';

// https://astro.build/config
export default defineConfig({
  site: 'https://poliureasystem.it',
  trailingSlash: 'never',
  output: 'server',
  adapter: cloudflare({ imageService: 'passthrough' }),
  session: false,

  vite: {
    plugins: [tailwindcss()]
  },

  integrations: [
    sitemap({
      filter: (page) =>
        !page.includes('/admin') &&
        !page.includes('/area-clienti') &&
        !page.includes('/accesso-preventivi') &&
        !page.includes('/404') &&
        !page.includes('/media/')
    })
  ]
});