import {
  CopilotRuntime,
  createCopilotEndpoint,
  InMemoryAgentRunner,
} from "@copilotkit/runtime/v2";
import { LangGraphAgent } from "@copilotkit/runtime/langgraph";
import { handle } from "hono/vercel";

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

function stripThinkingBlocks(content: string): string {
  let sanitized = content.replace(/<think>[\s\S]*?<\/think>/gi, "");
  sanitized = sanitized.replace(/<think>[\s\S]*$/gi, "");
  sanitized = sanitized.replace(/<\/think>/gi, "");
  return sanitized.trim();
}

function sanitizeMessageContent(content: unknown): unknown {
  if (typeof content === "string") {
    return stripThinkingBlocks(content);
  }

  if (Array.isArray(content)) {
    return content.map((part) => {
      if (typeof part === "string") {
        return stripThinkingBlocks(part);
      }

      if (part && typeof part === "object" && "text" in part) {
        const text = (part as { text?: unknown }).text;
        if (typeof text === "string") {
          return { ...part, text: stripThinkingBlocks(text) };
        }
      }

      return part;
    });
  }

  return content;
}

function isAssistantMessage(message: any): boolean {
  return message?.role === "assistant" || message?.type === "ai";
}

function isEmptyContent(content: unknown): boolean {
  if (typeof content === "string") {
    return content.trim().length === 0;
  }

  if (Array.isArray(content)) {
    return content.every((part) => {
      if (typeof part === "string") {
        return part.trim().length === 0;
      }
      if (part && typeof part === "object" && "text" in part) {
        const text = (part as { text?: unknown }).text;
        return typeof text !== "string" || text.trim().length === 0;
      }
      return false;
    });
  }

  return false;
}

function sanitizeMessages(messages: any[] | undefined): any[] | undefined {
  if (!Array.isArray(messages)) {
    return messages;
  }

  return messages
    .map((message) => {
      if (!isAssistantMessage(message)) {
        return message;
      }

      const sanitizedContent = sanitizeMessageContent(message.content);
      return {
        ...message,
        content: sanitizedContent,
      };
    })
    .filter((message) => !(isAssistantMessage(message) && isEmptyContent(message.content)));
}

function sanitizeAgentInput(input: any): any {
  if (!input || typeof input !== "object") {
    return input;
  }

  const sanitizedInput = {
    ...input,
    messages: sanitizeMessages(input.messages),
  };

  if (input.state && typeof input.state === "object") {
    sanitizedInput.state = {
      ...input.state,
      messages: sanitizeMessages(input.state.messages),
    };
  }

  return sanitizedInput;
}

let agentRunQueue: Promise<void> = Promise.resolve();

function enqueueAgentRun(task: () => Promise<void>): Promise<void> {
  const run = agentRunQueue.then(task, task);
  agentRunQueue = run.catch(() => undefined);
  return run;
}

function isTransientModelError(error: unknown): boolean {
  if (!(error instanceof Error)) {
    return false;
  }

  return (
    error.message.includes("InternalServerError") ||
    error.message.includes("An internal error occurred") ||
    error.message.includes("overloaded_error") ||
    error.message.includes("529")
  );
}

class ResilientLangGraphAgent extends LangGraphAgent {
  async runAgentStream(input: any, subscriber: any): Promise<void> {
    return enqueueAgentRun(async () => {
      let runInput = sanitizeAgentInput(input);
      const maxAttempts = 5;

      for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
        try {
          await super.runAgentStream(runInput, subscriber);
          return;
        } catch (error) {
          if (error instanceof Error && error.message.includes("Message not found")) {
            const fallbackInput = {
              ...runInput,
              threadId: undefined,
              forwardedProps: {
                ...(runInput?.forwardedProps ?? {}),
                command: undefined,
              },
            };
            runInput = sanitizeAgentInput(fallbackInput);
            continue;
          }

          if (!isTransientModelError(error) || attempt === maxAttempts) {
            throw new Error("模型服务当前繁忙，请稍后重试。");
          }

          const backoffMs = Math.min(30000, 1500 * 2 ** (attempt - 1));
          await delay(backoffMs);
        }
      }
    });
  }
}

const defaultAgent = new ResilientLangGraphAgent({
  deploymentUrl:
    process.env.AGENT_URL ||
    process.env.LANGGRAPH_DEPLOYMENT_URL ||
    "http://127.0.0.1:2024",
  graphId: "tripgenius_agent",
  langsmithApiKey: process.env.LANGSMITH_API_KEY || "",
});

const runtime = new CopilotRuntime({
  agents: { default: defaultAgent },
  runner: new InMemoryAgentRunner(),
  openGenerativeUI: true,
  a2ui: {
    injectA2UITool: false,
  },
  mcpApps: {
    servers: [
      {
        type: "http",
        url: process.env.MCP_SERVER_URL || "https://mcp.excalidraw.com",
        serverId: "example_mcp_app",
      },
    ],
  },
});

const app = createCopilotEndpoint({
  runtime,
  basePath: "/api/copilotkit",
});

export const GET = handle(app);
export const POST = handle(app);
