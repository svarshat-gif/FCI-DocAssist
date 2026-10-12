"use client";

import { History, Loader2, Search } from "lucide-react";
import { useInterface } from "@/contexts/interface-context";
import { Button } from "@/components/ui/button";
import type { Conversation } from "@/lib/types";
import { cn } from "@/lib/utils";

export type ChatHistoryProps = {
  conversations: Conversation[];
  activeConversationId?: string;
  query: string;
  onQueryChange: (query: string) => void;
  onSelectConversation: (id: string) => void;
  onLoadMore: () => void;
  onRetry: () => void;
  hasMore: boolean;
  loading: boolean;
  error: string | null;
  signedIn: boolean;
  disabled: boolean;
};

export function ChatHistory(props: ChatHistoryProps) {
  const t = useInterface();
  return (
    <section aria-label={t("History")}>
      <h2 className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase text-fci-steel dark:text-white/60">
        <History className="h-3.5 w-3.5" aria-hidden="true" />
        {t("History")}
      </h2>
      <label className="mb-3 flex items-center gap-2 border-b border-fci-line pb-2 dark:border-white/10">
        <Search className="h-4 w-4 shrink-0 text-fci-steel" aria-hidden="true" />
        <input type="search" aria-label="Search previous chats" placeholder="Search previous chats" maxLength={200}
          value={props.query} onChange={(event) => props.onQueryChange(event.target.value)} disabled={!props.signedIn}
          className="h-8 min-w-0 w-full bg-transparent text-sm outline-none placeholder:text-fci-steel/70" />
      </label>
      <div className="space-y-1" aria-busy={props.loading}>
        {props.conversations.map((conversation) => (
          <button key={conversation.id} type="button" title={conversation.title}
            disabled={props.disabled} aria-current={props.activeConversationId === conversation.id ? "page" : undefined}
            onClick={() => props.onSelectConversation(conversation.id)}
            className={cn("w-full min-w-0 rounded-lg px-3 py-2 text-left text-sm transition disabled:opacity-60",
              props.activeConversationId === conversation.id ? "bg-fci-light font-medium text-fci-dark dark:bg-fci-primary/20 dark:text-fci-light" : "text-fci-steel hover:bg-fci-mist dark:text-white/70 dark:hover:bg-white/10")}>
            <span className="line-clamp-2 break-words">{conversation.title}</span>
            <time dateTime={conversation.updated_at} className="mt-1 block text-xs text-fci-steel dark:text-white/50">
              {new Date(conversation.updated_at).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric", timeZone: "Asia/Kolkata" })}
            </time>
          </button>
        ))}
        {props.error ? <div role="alert" className="py-2 text-sm text-red-700 dark:text-red-300">
          {props.error}<Button variant="ghost" className="mt-1" onClick={props.onRetry} disabled={props.loading}>Try again</Button>
        </div> : null}
        {props.loading ? <div role="status" className="flex items-center gap-2 py-3 text-sm text-fci-steel"><Loader2 className="h-4 w-4 animate-spin" />Loading chats...</div> : null}
        {!props.loading && !props.error && !props.conversations.length ? <p className="py-3 text-sm text-fci-steel dark:text-white/60">
          {!props.signedIn ? "Sign in to see your previous chats." : props.query ? "No matching chats." : t("No saved chats yet.")}
        </p> : null}
        {props.hasMore && !props.error ? <Button variant="ghost" className="w-full" disabled={props.loading || props.disabled} onClick={props.onLoadMore}>Load older chats</Button> : null}
      </div>
    </section>
  );
}
