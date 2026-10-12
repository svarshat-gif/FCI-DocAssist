"use client";

import { useInterface } from "@/contexts/interface-context";
import {
  Bookmark,
  ChevronLeft,
  ChevronRight,
  MessageSquarePlus,
  Settings,
  Sparkles,
} from "lucide-react";
import { CircularSearch } from "@/components/chat/circular-search";
import { BookmarkPanel } from "@/components/chat/bookmarks";
import { ChatHistory, type ChatHistoryProps } from "@/components/chat/chat-history";
import { LanguageSelector } from "@/components/chat/language-selector";
import { Button } from "@/components/ui/button";
import type { SupportedLanguage } from "@/lib/languages";
import type { Circular } from "@/lib/types";
import { cn } from "@/lib/utils";

type AppSidebarProps = {
  collapsed: boolean;
  onCollapsedChange: (collapsed: boolean) => void;
  history: ChatHistoryProps;
  recentCirculars: Circular[];
  language: SupportedLanguage;
  onLanguageChange: (language: SupportedLanguage) => void;
  onNewChat: () => void;
  onAsk: (question: string) => void;
  onSummarize: (circularId: string, style: "short" | "detailed" | "bullets") => void;
  onOpenSettings: () => void;
};

export function AppSidebar({
  collapsed,
  onCollapsedChange,
  history,
  recentCirculars,
  language,
  onLanguageChange,
  onNewChat,
  onAsk,
  onSummarize,
  onOpenSettings,
}: AppSidebarProps) {
  const t = useInterface();
  return (
    <aside
      className={cn(
        "hidden h-screen shrink-0 border-r border-fci-line bg-white/90 backdrop-blur-xl transition-all dark:border-white/10 dark:bg-[#101712]/90 lg:flex lg:flex-col",
        collapsed ? "w-[96px]" : "w-[300px]",
      )}
    >
      <div className={cn("flex h-16 items-center justify-between border-b border-fci-line dark:border-white/10", collapsed ? "px-2" : "px-4")}>
        <div className={cn("flex items-center gap-2", collapsed && "justify-center")}>
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-fci-primary text-white">
            <Sparkles className="h-4 w-4" aria-hidden="true" />
          </div>
          {!collapsed ? (
            <div>
              <div className="text-sm font-semibold text-fci-ink dark:text-white">
                FCI Doc Assist
              </div>
              <div className="text-xs text-fci-steel dark:text-white/60">Circulars &amp; documents</div>
            </div>
          ) : null}
        </div>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          onClick={() => onCollapsedChange(!collapsed)}
        >
          {collapsed ? (
            <ChevronRight className="h-4 w-4" aria-hidden="true" />
          ) : (
            <ChevronLeft className="h-4 w-4" aria-hidden="true" />
          )}
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        <Button type="button" className="w-full" onClick={onNewChat}>
          <MessageSquarePlus className="h-4 w-4" aria-hidden="true" />
          {!collapsed ? t("New chat") : null}
        </Button>

        {!collapsed ? (
          <div className="mt-5 space-y-6">
            <ChatHistory {...history} />

            <section>
              <div className="mb-3 text-xs font-semibold uppercase tracking-[0.16em] text-fci-steel dark:text-white/60">
                {t("Circular search")}
              </div>
              <CircularSearch onAsk={onAsk} onSummarize={onSummarize} />
            </section>

            <section>
              <div className="mb-3 text-xs font-semibold uppercase tracking-[0.16em] text-fci-steel dark:text-white/60">
                {t("Recent circulars")}
              </div>
              <div className="space-y-2">
                {recentCirculars.length ? (
                  recentCirculars.slice(0, 5).map((item) => (
                    <a
                      key={item.id}
                      href={item.official_url}
                      target="_blank"
                      rel="noreferrer"
                      className="block rounded-lg border border-fci-line bg-fci-mist/70 p-3 text-sm transition hover:border-fci-primary/30 dark:border-white/10 dark:bg-white/10"
                    >
                      <span className="line-clamp-2 font-medium text-fci-ink dark:text-white">
                        {item.title}
                      </span>
                      <span className="mt-1 block text-xs text-fci-steel dark:text-white/60">
                        {item.publication_date || "Date unavailable"}
                      </span>
                    </a>
                  ))
                ) : (
                  <p className="rounded-lg border border-dashed border-fci-line p-3 text-sm text-fci-steel dark:border-white/10 dark:text-white/60">
                    No circulars are available yet.
                  </p>
                )}
              </div>
            </section>

            <section>
              <div className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-fci-steel dark:text-white/60">
                <Bookmark className="h-3.5 w-3.5" aria-hidden="true" />
                {t("Bookmarks")}
              </div>
              <BookmarkPanel onAsk={onAsk} />
            </section>
          </div>
        ) : null}
      </div>

      <div className="space-y-3 border-t border-fci-line p-4 dark:border-white/10">
        {!collapsed ? (
          <LanguageSelector value={language} onChange={onLanguageChange} />
        ) : null}
        <Button
          type="button"
          variant="secondary"
          size={collapsed ? "icon" : "md"}
          className={collapsed ? "w-full" : "w-full"}
          onClick={onOpenSettings}
          aria-label="Open settings"
        >
          <Settings className="h-4 w-4" aria-hidden="true" />
          {!collapsed ? t("Settings") : null}
        </Button>
      </div>
    </aside>
  );
}
