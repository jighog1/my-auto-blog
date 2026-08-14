import satori from "satori";
import { SITE } from "@/config";
import loadGoogleFonts from "../loadGoogleFont";

export default async () =>
  satori(
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
          padding: "64px 72px",
          borderTop: "18px solid #1757d3",
          fontFamily: "Noto Sans KR",
        },
        children: [
          {
            type: "div",
            props: {
              style: {
                display: "flex",
                color: "#1757d3",
                fontSize: 26,
                fontWeight: 700,
              },
              children: "AI BRIEFING ROOM",
            },
          },
          {
            type: "div",
            props: {
              style: { display: "flex", flexDirection: "column" },
              children: [
                {
                  type: "div",
                  props: {
                    style: {
                      display: "flex",
                      fontSize: 88,
                      fontWeight: 700,
                      letterSpacing: "-4px",
                    },
                    children: SITE.title,
                  },
                },
                {
                  type: "div",
                  props: {
                    style: {
                      display: "flex",
                      marginTop: 18,
                      fontSize: 36,
                      color: "#62676f",
                    },
                    children: SITE.tagline,
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
                justifyContent: "space-between",
                fontSize: 24,
                color: "#62676f",
              },
              children: [
                "30초 핵심 · 업무 적용 · 원문 확인",
                new URL(SITE.website).hostname,
              ],
            },
          },
        ],
      },
    },
    {
      width: 1200,
      height: 630,
      embedFont: true,
      fonts: await loadGoogleFonts(
        SITE.title +
          SITE.tagline +
          SITE.website +
          "30초 핵심 업무 적용 원문 확인"
      ),
    }
  );
