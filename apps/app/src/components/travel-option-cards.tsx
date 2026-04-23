"use client";

import { useAgent } from "@copilotkit/react-core/v2";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

function isAssistantLikeMessage(message: unknown): boolean {
  if (!message || typeof message !== "object") return false;
  const candidate = message as { role?: unknown; type?: unknown };
  return (
    candidate.role === "assistant" ||
    candidate.role === "ai" ||
    candidate.type === "assistant" ||
    candidate.type === "ai"
  );
}

function isToolLikeMessage(message: unknown): boolean {
  if (!message || typeof message !== "object") return false;
  const candidate = message as { role?: unknown; type?: unknown };
  return candidate.role === "tool" || candidate.type === "tool";
}

function isOptionSourceMessage(message: unknown): boolean {
  return isAssistantLikeMessage(message) || isToolLikeMessage(message);
}

function stripThinkingBlocks(content: string): string {
  let sanitized = content.replace(/<think>[\s\S]*?<\/think>/gi, "");
  sanitized = sanitized.replace(/<think>[\s\S]*$/gi, "");
  sanitized = sanitized.replace(/<\/think>/gi, "");
  return sanitized;
}

function normalizeMessageContent(content: unknown): string {
  if (typeof content === "string") return content;
  if (content && typeof content === "object" && "text" in content) {
    const text = (content as { text?: unknown }).text;
    return typeof text === "string" ? text : "";
  }
  if (Array.isArray(content)) {
    return content
      .map((part) => {
        if (typeof part === "string") return part;
        if (part && typeof part === "object" && "text" in part) {
          const text = (part as { text?: unknown }).text;
          return typeof text === "string" ? text : "";
        }
        return "";
      })
      .join("\n")
      .trim();
  }
  return "";
}

function normalizeOptionLabel(raw: string): string {
  return raw
    .replace(/^[\s"'“”‘’]+|[\s"'“”‘’]+$/g, "")
    .replace(/[。！!？?，,；;：:]+$/g, "")
    .trim();
}

function extractOptions(text: string): string[] {
  const safeText = stripThinkingBlocks(text);
  const candidates: string[] = [];

  const bracketPatterns = [
    /（([^）]*\/[^）]*)）/g,
    /\(([^)]*\/[^)]*)\)/g,
    /可选项[:：]\s*([^\n]+)/g,
    /比如[:：]\s*([^\n]+)/g,
  ];

  for (const pattern of bracketPatterns) {
    for (const match of safeText.matchAll(pattern)) {
      const raw = (match[1] || "").trim();
      if (!raw) continue;
      const parts = raw
        .split(/[\/|、,，]/)
        .map((s) => normalizeOptionLabel(s))
        .filter((s) => s.length > 0 && s.length <= 16);
      candidates.push(...parts);
    }
  }

  const lines = safeText
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);

  for (const line of lines) {
    const lineOptionMatch = line.match(
      /^(?:[-*•]\s*)?(?:\d+[.)、]\s*)?(?:[一二三四五六七八九十]+[、.．]\s*)?([A-Za-z\u4e00-\u9fa5][A-Za-z0-9\u4e00-\u9fa5\-+ ]{0,18}?)\s*[—\-:：]\s*.+$/,
    );

    if (lineOptionMatch) {
      const option = normalizeOptionLabel(lineOptionMatch[1]);
      if (option.length > 0 && option.length <= 16) {
        candidates.push(option);
      }
    }
  }

  return [...new Set(candidates)].slice(0, 6);
}

function extractQuestion(text: string): string {
  const lines = stripThinkingBlocks(text)
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);

  const questionByPunctuation = lines.find((line) => /[？?]$/.test(line));
  if (questionByPunctuation) {
    return questionByPunctuation;
  }

  const questionLikePattern =
    /请问|多少|几天|预算|花费|费用|风格|偏好|交通|哪种|几位|入住|房型|出发|哪个城市|同行|人数/;
  const questionByIntent = lines.find((line) => questionLikePattern.test(line));
  if (questionByIntent) {
    return questionByIntent;
  }

  // In multi-line tool messages, the prompt is often in later lines.
  return lines[lines.length - 1] || "请选择一个选项";
}

function inferOptionsFromQuestion(question: string): string[] {
  const q = question.toLowerCase();

  if (/玩几天|几天|天数/.test(q)) {
    return ["3天", "5天", "7天"];
  }

  if (/预算|花多少钱|费用|花费/.test(q)) {
    return ["预算随便", "5000元", "8000元", "10000元"];
  }

  if (/风格|偏好|倾向/.test(q)) {
    return ["chill", "美食", "打卡", "出片"];
  }

  if (/交通|怎么过去|怎么去|交通方式/.test(q)) {
    return ["飞机", "高铁"];
  }

  if (/几个人|同行|间房|房间/.test(q)) {
    return ["1个人，1间房", "2个人，1间房", "2个人，2间房"];
  }

  return [];
}

function inferFromAgentState(state: unknown): { question: string; options: string[] } {
  if (!state || typeof state !== "object") {
    return { question: "", options: [] };
  }

  const typedState = state as {
    current_step?: unknown;
    travel_request?: { destination?: unknown };
  };

  const currentStep =
    typeof typedState.current_step === "string" ? typedState.current_step : "";
  const destination =
    typeof typedState.travel_request?.destination === "string"
      ? typedState.travel_request.destination
      : "";

  if (currentStep.includes("days")) {
    return {
      question: destination
        ? `请问您计划去${destination}玩几天呢？`
        : "请问您计划玩几天呢？",
      options: ["3天", "5天", "7天"],
    };
  }

  if (currentStep.includes("budget")) {
    return {
      question: "你的预算大概是多少呢？",
      options: ["预算随便", "5000元", "8000元", "10000元"],
    };
  }

  if (currentStep.includes("style")) {
    return {
      question: "你更偏好哪种旅行风格？",
      options: ["chill", "美食", "打卡", "出片"],
    };
  }

  if (currentStep.includes("transport")) {
    return {
      question: "你更倾向哪种交通方式？",
      options: ["飞机", "高铁"],
    };
  }

  if (currentStep.includes("travelers") || currentStep.includes("room")) {
    return {
      question: "本次出行人数和房间需求是？",
      options: ["1个人，1间房", "2个人，1间房", "2个人，2间房"],
    };
  }

  return { question: "", options: [] };
}

export function TravelOptionCards() {
  const { agent } = useAgent({ agentId: "default" });
  const stateFallback = inferFromAgentState(agent.state);

  const recentAssistantTexts = [...agent.messages]
    .reverse()
    .filter((message) => isOptionSourceMessage(message))
    .slice(0, 6)
    .map((message) => normalizeMessageContent(message.content))
    .filter((text) => text.length > 0);

  const latestAssistantText = recentAssistantTexts[0] || "";

  const fromLatest = extractOptions(latestAssistantText);
  const parsedQuestion = extractQuestion(latestAssistantText);
  const fromLatestQuestion = inferOptionsFromQuestion(parsedQuestion);

  let options = fromLatest;

  if (options.length < 2 && fromLatestQuestion.length >= 2) {
    options = fromLatestQuestion;
  }

  if (options.length < 2 && stateFallback.options.length >= 2) {
    options = stateFallback.options;
  }

  if (options.length < 2) {
    for (const text of recentAssistantTexts.slice(1)) {
      const parsed = extractOptions(text);
      if (parsed.length >= 2) {
        options = parsed;
        break;
      }
    }
  }

  const question = parsedQuestion || stateFallback.question || "请选择一个选项";

  if (options.length < 2) {
    return null;
  }

  return (
    <Card className="mx-4 mb-4 border-[var(--border)] bg-[var(--card)]">
      <CardHeader className="px-4 py-3">
        <CardTitle className="text-sm">{question}</CardTitle>
      </CardHeader>
      <CardContent className="px-4 pb-4 pt-0">
        <div className="flex flex-wrap gap-2">
          {options.map((option) => (
            <Button
              key={option}
              type="button"
              size="sm"
              variant="secondary"
              disabled={agent.isRunning}
              onClick={() => {
                if (agent.isRunning) return;
                agent.addMessage({
                  role: "user",
                  id: crypto.randomUUID(),
                  content: option,
                });
                agent.runAgent();
              }}
            >
              {option}
            </Button>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
