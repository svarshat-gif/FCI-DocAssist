"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Bot, UserRound } from "lucide-react";
import { CitationCard } from "@/components/chat/citation-card";
import type { ChatMessage } from "@/lib/types";
import { cn } from "@/lib/utils";

type MessageBubbleProps = {
  message: ChatMessage;
  fontScale: number;
};

export function MessageBubble({ message, fontScale }: MessageBubbleProps) {
  const isAssistant = message.role === "assistant";

  return (
    <div
      className={cn(
        "flex w-full gap-3",
        isAssistant ? "justify-start" : "justify-end",
      )}
    >
      {isAssistant ? (
        <div className="mt-1 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-fci-primary text-white shadow-crisp">
          <Bot className="h-4 w-4" aria-hidden="true" />
        </div>
      ) : null}

      <div
        className={cn(
          "max-w-[min(780px,100%)] rounded-lg px-4 py-3 shadow-sm",
          isAssistant
            ? "border border-fci-line bg-white text-fci-ink dark:border-white/10 dark:bg-white/10 dark:text-white"
            : "bg-fci-primary text-white",
        )}
        style={{ fontSize: `${fontScale}rem` }}
      >
        <div className="markdown-body leading-7">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
        </div>

        {isAssistant && message.citations?.length ? (
          <div className="mt-4 grid gap-3">
            {message.citations.map((citation) => (
              <CitationCard key={`${citation.source_id}-${citation.title}`} citation={citation} />
            ))}
          </div>
        ) : null}
      </div>

      {!isAssistant ? (
        <div className="mt-1 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-white text-fci-primary shadow-sm dark:bg-white/10">
          <UserRound className="h-4 w-4" aria-hidden="true" />
        </div>
      ) : null}
    </div>
  );
}
