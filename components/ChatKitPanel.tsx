"use client";

import { useCallback, useRef, useState } from "react";
import { ChatKit, useChatKit } from "@openai/chatkit-react";
import type { Widgets } from "@openai/chatkit";
import {
  STARTER_PROMPTS,
  PLACEHOLDER_INPUT,
  GREETING,
  CHATKIT_API_URL,
  CHATKIT_API_DOMAIN_KEY,
  getThemeConfig,
} from "@/lib/config";
import { ErrorOverlay } from "./ErrorOverlay";
import type { ColorScheme } from "@/hooks/useColorScheme";

type ChatKitPanelProps = {
  theme: ColorScheme;
  onResponseEnd: () => void;
  onThemeRequest: (scheme: ColorScheme) => void;
};

const isDev = process.env.NODE_ENV !== "production";

export function ChatKitPanel({
  theme,
  onResponseEnd,
  onThemeRequest,
}: ChatKitPanelProps) {
  const chatkitRef = useRef<ReturnType<typeof useChatKit> | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Handle widget actions - send quiz.submit and quiz.reset to the server
  const handleWidgetAction = useCallback(
    async (
      action: { type: string; payload?: Record<string, unknown> },
      widgetItem: { id: string; widget: Widgets.Card | Widgets.ListView }
    ) => {
      const chatkit = chatkitRef.current;
      if (!chatkit) {
        console.warn("ChatKit not initialized");
        return;
      }

      console.log("[ChatKitPanel] Widget action received:", action.type, action.payload);

      // Both quiz.submit and quiz.reset are handled server-side
      if (action.type === "quiz.submit" || action.type === "quiz.reset") {
        console.log(`[ChatKitPanel] Sending ${action.type} to server`);
        await chatkit.sendCustomAction(action, widgetItem.id);
        return;
      }

      console.log("[ChatKitPanel] Unhandled action type:", action.type);
    },
    []
  );

  const chatkit = useChatKit({
    api: {
      url: CHATKIT_API_URL,
      domainKey: CHATKIT_API_DOMAIN_KEY,
      uploadStrategy: { type: "two_phase" },
    },
    theme: {
      colorScheme: theme,
      density: "spacious",
      ...getThemeConfig(theme),
    },
    startScreen: {
      greeting: GREETING,
      prompts: STARTER_PROMPTS,
    },
    composer: {
      placeholder: PLACEHOLDER_INPUT,
      attachments: {
        enabled: true,
      },
    },
    threadItemActions: {
      feedback: false,
    },
    widgets: {
      onAction: handleWidgetAction,
    },
    onClientTool: async (invocation: {
      name: string;
      params: Record<string, unknown>;
    }) => {
      if (isDev) {
        console.log("[ChatKitPanel] Client tool invocation:", invocation);
      }

      if (invocation.name === "switch_theme") {
        const requested = invocation.params.theme;
        if (requested === "light" || requested === "dark") {
          onThemeRequest(requested);
          return { success: true };
        }
        return { success: false };
      }

      return { success: false };
    },
    onResponseEnd: () => {
      onResponseEnd();
    },
    onError: ({ error: err }: { error: unknown }) => {
      console.error("[ChatKitPanel] Error:", err);
      if (err instanceof Error) {
        setError(err.message);
      }
    },
    onLog: ({ name, data }: { name: string; data?: Record<string, unknown> }) => {
      if (isDev) {
        console.debug("[chatkit]", name, data ?? {});
      }
    },
  });

  // Store ref for use in callbacks
  chatkitRef.current = chatkit;

  return (
    <div className="relative pb-8 flex h-[90vh] w-full rounded-2xl flex-col overflow-hidden bg-white shadow-sm transition-colors dark:bg-slate-900">
      <ChatKit
        control={chatkit.control}
        className="block h-full w-full"
      />
      <ErrorOverlay
        error={error}
        fallbackMessage={null}
        onRetry={null}
        retryLabel="Restart chat"
      />
    </div>
  );
}
