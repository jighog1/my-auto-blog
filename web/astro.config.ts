import { defineConfig, envField, fontProviders } from "astro/config";
import type { Html, Root } from "mdast";
import { visit } from "unist-util-visit";
import tailwindcss from "@tailwindcss/vite";
import sitemap from "@astrojs/sitemap";
import { unified } from "@astrojs/markdown-remark";
import remarkToc from "remark-toc";
import remarkCollapse from "remark-collapse";
import {
  transformerNotationDiff,
  transformerNotationHighlight,
  transformerNotationWordHighlight,
} from "@shikijs/transformers";
import { transformerFileName } from "./src/utils/transformers/fileName";
import { SITE } from "./src/config";

const escapeHtml = (value: string) =>
  value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");

function remarkMermaidBlocks() {
  return (tree: Root) => {
    visit(tree, "code", (node, index, parent) => {
      if (node.lang !== "mermaid" || index === undefined || !parent) return;
      const mermaidNode: Html = {
        type: "html",
        value: `<pre class="mermaid">${escapeHtml(node.value)}</pre>`,
      };
      parent.children[index] = mermaidNode;
    });
  };
}

// https://astro.build/config
export default defineConfig({
  site: SITE.website,
  base: "/",
  integrations: [
    sitemap({
      filter: page => SITE.showArchives || !page.endsWith("/archives"),
    }),
  ],
  markdown: {
    processor: unified({
      remarkPlugins: [
        remarkMermaidBlocks,
        remarkToc,
        [remarkCollapse, { test: "Table of contents" }],
      ],
    }),
    shikiConfig: {
      // For more themes, visit https://shiki.style/themes
      themes: { light: "light-plus", dark: "dark-plus" },
      defaultColor: false,
      wrap: false,
      transformers: [
        transformerFileName({ style: "v2", hideDot: false }),
        transformerNotationHighlight(),
        transformerNotationWordHighlight(),
        transformerNotationDiff({ matchAlgorithm: "v3" }),
      ],
    },
  },
  vite: {
    plugins: [tailwindcss()],
    optimizeDeps: {
      exclude: ["@resvg/resvg-js"],
    },
  },
  image: {
    responsiveStyles: true,
    layout: "constrained",
  },
  env: {
    schema: {
      PUBLIC_GOOGLE_SITE_VERIFICATION: envField.string({
        access: "public",
        context: "client",
        optional: true,
      }),
    },
  },
  fonts: [
    {
      name: "Google Sans Code",
      cssVariable: "--font-google-sans-code",
      provider: fontProviders.google(),
      fallbacks: ["monospace"],
      weights: [300, 400, 500, 600, 700],
      styles: ["normal", "italic"],
    },
  ],
});
