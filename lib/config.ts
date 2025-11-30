import { ColorScheme, StartScreenPrompt, ThemeOption } from "@openai/chatkit";

// Custom backend URL (FastAPI server)
export const CHATKIT_API_URL =
  process.env.NEXT_PUBLIC_CHATKIT_API_URL?.trim() || "http://127.0.0.1:8087/chatkit";

// Domain key for ChatKit (can be any non-empty string for local dev)
export const CHATKIT_API_DOMAIN_KEY =
  process.env.NEXT_PUBLIC_CHATKIT_DOMAIN_KEY?.trim() || "domain_pk_local_dev";

export const STARTER_PROMPTS: StartScreenPrompt[] = [
  // {
  //   label: "Create a quiz from a PDF",
  //   prompt: "Create a quiz about world capitals",
  //   icon: "circle-question",
  // },
  // {
  //   label: "Science quiz",
  //   prompt: "Give me a quiz about the solar system",
  //   icon: "sparkle",
  // },
];

export const PLACEHOLDER_INPUT = "Upload a PDF for a custom quiz...";

export const GREETING = "Hi! I'm The Quizzler. Upload a PDF for a custom quiz!";

export const getThemeConfig = (theme: ColorScheme): ThemeOption => ({
  color: {
    grayscale: {
      hue: 220,
      tint: 6,
      shade: theme === "dark" ? -1 : -4,
    },
    accent: {
      primary: theme === "dark" ? "#f1f5f9" : "#0f172a",
      level: 1,
    },
  },
  radius: "round",
  // Add other theme options here
  // chatkit.studio/playground to explore config options
});
