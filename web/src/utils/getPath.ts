export function getPath(
  id: string,
  _filePath: string | undefined,
  includeBase = true
) {
  // id is like "auto-post-20260407162620" or "subdir/post-name"
  // We only want the last segment (the slug itself), ignoring sub-directories
  const slug = id.split("/").pop() ?? id;

  const basePath = includeBase ? "posts" : "";

  const path = basePath ? `${basePath}/${slug}` : slug;

  return `${import.meta.env.BASE_URL}${path}`;
}
