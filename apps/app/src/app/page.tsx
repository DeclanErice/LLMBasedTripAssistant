"use client";

import { useMemo, useState } from "react";
import { ExampleLayout } from "@/components/example-layout";
import { ExampleCanvas } from "@/components/example-canvas";
import { TravelOptionCards } from "@/components/travel-option-cards";
import { useGenerativeUIExamples } from "@/hooks";

import { CopilotChat, CopilotChatAssistantMessage } from "@copilotkit/react-core/v2";

function stripThinkingBlocks(content: string): string {
  let sanitized = content.replace(/<think>[\s\S]*?<\/think>/gi, "");
  // During streaming a <think> block may be opened before closing tag arrives.
  sanitized = sanitized.replace(/<think>[\s\S]*$/gi, "");
  sanitized = sanitized.replace(/<\/think>/gi, "");
  return sanitized;
}

function sanitizeAssistantContent(content: string): string {
  const lines = stripThinkingBlocks(content)
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);

  const hiddenPatterns = [
    /根据工具/i,
    /调用\s*[a-zA-Z_]+/i,
    /start_travel_planning/i,
    /confirm_start_date/i,
    /confirm_departure_city/i,
    /confirm_transport/i,
    /confirm_travelers/i,
    /generate_itinerary/i,
    /工具参数/i,
    /流程/i,
    /我需要先/i,
    /我应该先/i,
    /看工具说明/i,
    /内部推理/i,
  ];

  const visible = lines.filter((line) => !hiddenPatterns.some((pattern) => pattern.test(line)));

  if (visible.length === 0) {
    return "";
  }

  return visible.join("\n\n");
}

export default function HomePage() {
  const [friendlyError, setFriendlyError] = useState<string>("");

  useGenerativeUIExamples();

  const markdownRenderer = useMemo(
    () =>
      ({ content }: { content: string }) => {
        const sanitized = sanitizeAssistantContent(content);
        if (!sanitized) {
          return null;
        }
        return <CopilotChatAssistantMessage.MarkdownRenderer content={sanitized} />;
      },
    [],
  );

  const reasoningRenderer = useMemo(
    () =>
      ({ message }: { message: { content?: unknown } }) => {
        const raw = typeof message?.content === "string" ? message.content : "";
        const sanitized = sanitizeAssistantContent(raw);
        if (!sanitized) {
          return null;
        }
        return <CopilotChatAssistantMessage.MarkdownRenderer content={sanitized} />;
      },
    [],
  );

  return (
    <ExampleLayout
      chatContent={
        <div className="h-full flex flex-col">
          <div className="flex-1 min-h-0">
            <CopilotChat
              agentId="default"
              input={{ disclaimer: () => null, className: "pb-6" }}
              onError={({ error }) => {
                if (
                  error.message.includes("internal error") ||
                  error.message.includes("InternalServerError") ||
                  error.message.includes("529")
                ) {
                  setFriendlyError("模型服务暂时繁忙，请稍后重试。你也可以直接再次发送上一条消息。");
                }
              }}
              messageView={{
                reasoningMessage: reasoningRenderer,
                assistantMessage: {
                  markdownRenderer,
                  toolCallsView: () => null,
                },
              }}
            />
          </div>
          {friendlyError ? (
            <div className="mx-4 mb-2 rounded-md border border-[var(--border)] bg-[var(--secondary)] px-3 py-2 text-sm text-[var(--muted-foreground)]">
              {friendlyError}
            </div>
          ) : null}
          <TravelOptionCards />
        </div>
      }
      appContent={<ExampleCanvas />}
    />
  );
}
