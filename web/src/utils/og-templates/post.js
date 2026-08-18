import satori from "satori";
import { SITE } from "@/config";
import loadGoogleFonts from "../loadGoogleFont";

export default async post => {
  const author =
    post.data.author === "AI Bot" ? "AI 자동 작성" : post.data.author;
  const date = new Intl.DateTimeFormat("ko-KR", {
    timeZone: SITE.timezone,
    year: "numeric",
    month: "long",
    day: "numeric",
  }).format(post.data.pubDatetime);
  const fontText = `AI BRIEFING${SITE.title}${SITE.tagline}${post.data.title}${author}${date}`;

  return satori(
    {
      type: "div",
      props: {
        style: {
          background: "#f7f6f2",
          color: "#1b1f23",
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: "58px 68px",
          borderTop: "18px solid #1757d3",
          fontFamily: "Noto Sans KR",
        },
        children: [
          {
            type: "div",
            props: {
              style: {
                display: "flex",
                justifyContent: "space-between",
                fontSize: 25,
                fontWeight: 700,
              },
              children: [
                {
                  type: "span",
                  props: { style: { color: "#1757d3" }, children: SITE.title },
                },
                {
                  type: "span",
                  props: {
                    style: { color: "#62676f" },
                    children: "AI BRIEFING",
                  },
                },
              ],
            },
          },
          {
            type: "div",
            props: {
              style: {
                display: "flex",
                maxHeight: "360px",
                overflow: "hidden",
                fontSize: post.data.title.length > 48 ? 54 : 64,
                lineHeight: 1.25,
                fontWeight: 700,
                letterSpacing: "-2px",
              },
              children: post.data.title,
            },
          },
          {
            type: "div",
            props: {
              style: {
                display: "flex",
                justifyContent: "space-between",
                fontSize: 24,
                color: "#62676f",
              },
              children: [author, date],
            },
          },
        ],
      },
    },
    {
      width: 1200,
      height: 630,
      embedFont: true,
      fonts: await loadGoogleFonts(fontText),
    }
  );
};
