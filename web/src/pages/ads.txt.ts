import type { APIRoute } from "astro";

export const GET: APIRoute = () => {
  const adsTxtContent = `google.com, pub-1889114264117113, DIRECT, f08c47fec0942fa0`;
  
  return new Response(adsTxtContent, {
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
    },
  });
};
