import { slugifyStr } from "./slugify";

/**
 * Get full path of a blog post
 * @param id - id of the blog post (the filename without extension, or subdir/filename)
 * @param filePath - unused (kept for API compatibility)
 * @param includeBase - whether to include `posts/` in return value
 * @returns blog post path including BASE_URL
 */
export function getPath(
  id: string,
  filePath: string | undefined,
  includeBase = true
) {
  // id is like "auto-post-20260407162620" or "subdir/post-name"
  // We only want the last segment (the slug itself), ignoring sub-directories
  const slug = id.split("/").pop() ?? id;

  const basePath = includeBase ? "posts" : "";

  const path = basePath ? `${basePath}/${slug}` : slug;

  return `${import.meta.env.BASE_URL}${path}`;
}
