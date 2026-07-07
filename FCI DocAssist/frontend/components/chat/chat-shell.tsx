"use client";

import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import {
  Loader2,
  Menu,
  MessageSquarePlus,
  PanelRightOpen,
  Search,
  Settings,
  ShieldCheck,
  X,
} from "lucide-react";
import { AppSidebar } from "@/components/layout/app-sidebar";
import { ChatComposer } from "@/components/chat/chat-composer";
import { CitationCard } from "@/components/chat/citation-card";
import { LanguageSelector } from "@/components/chat/language-selector";
import { MessageBubble } from "@/components/chat/message-bubble";
import { SettingsPanel } from "@/components/chat/settings-panel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/contexts/auth-context";
import { api } from "@/lib/api";
import type { SupportedLanguage } from "@/lib/languages";
import type { ChatMessage, Circular, Citation, Conversation, UploadSession } from "@/lib/types";
import { cn } from "@/lib/utils";

const suggestions = [
  "What is the transfer policy?",
  "Which circular mentions maternity leave?",
  "Summarize Circular 18/2024",
  "What does the promotion circular say?",
];

export function ChatShell() {
  const searchParams = useSearchParams();
  const { token, user, logout } = useAuth();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversationId, setConversationId] = useState<string | undefined>();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [recentCirculars, setRecentCirculars] = useState<Circular[]>([]);
  const [language, setLanguage] = useState<SupportedLanguage>("English");
  const [fontScale, setFontScale] = useState(1);
  const [loading, setLoading] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [sourceMode, setSourceMode] = useState<"official" | "upload">("official");
  const [uploadSession, setUploadSession] = useState<UploadSession | null>(null);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const consumedInitialPrompt = useRef(false);

  const latestCitations = useMemo<Citation[]>(() => {
    return [...messages].reverse().find((message) => message.citations?.length)?.citations ?? [];
  }, [messages]);

  const loadConversations = useCallback(async () => {
    const items = await api.conversations(token).catch(() => []);
    setConversations(items);
  }, [token]);

  useEffect(() => {
    loadConversations();
    api.recentCirculars().then(setRecentCirculars).catch(() => setRecentCirculars([]));
  }, [loadConversations]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, loading]);

  const sendMessage = useCallback(
    async (content: string) => {
      if (loading) {
        return;
      }
      setError(null);
      const userMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: "user",
        content,
      };
      setMessages((current) => [...current, userMessage]);
      setLoading(true);

      try {
        const response = await api.chat(
          {
            message: content,
            conversation_id: conversationId,
            language,
            source_mode: sourceMode,
            upload_session_id: sourceMode === "upload" ? uploadSession?.id : undefined,
          },
          token,
        );
        setConversationId(response.conversation_id);
        await renderAssistant(response.answer, response.citations);
        await loadConversations();
      } catch (caught) {
        const message = caught instanceof Error ? caught.message : "Unable to answer right now.";
        setError(message);
        setMessages((current) => [
          ...current,
          {
            id: crypto.randomUUID(),
            role: "assistant",
            content: message,
            citations: [],
          },
        ]);
      } finally {
        setLoading(false);
      }
    },
    [
      conversationId,
      language,
      loadConversations,
      loading,
      sourceMode,
      token,
      uploadSession?.id,
    ],
  );

  const summarizeCircular = useCallback(
    async (circularId: string, style: "short" | "detailed" | "bullets") => {
      if (loading) {
        return;
      }
      setError(null);
      setLoading(true);
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "user",
          content: `Create a ${style} summary of this circular.`,
        },
      ]);
      try {
        const response = await api.summarize(
          {
            circular_id: circularId,
            style,
            language,
          },
          token,
        );
        await renderAssistant(response.summary, response.citations);
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : "Unable to summarize circular.");
      } finally {
        setLoading(false);
      }
    },
    [language, loading, token],
  );

  useEffect(() => {
    const prompt = searchParams.get("prompt");
    if (prompt && !consumedInitialPrompt.current) {
      consumedInitialPrompt.current = true;
      sendMessage(prompt);
    }
  }, [searchParams, sendMessage]);

  async function renderAssistant(answer: string, citations: Citation[]) {
    const id = crypto.randomUUID();
    setMessages((current) => [...current, { id, role: "assistant", content: "", citations: [] }]);
    const words = answer.split(" ");
    for (let index = 0; index < words.length; index += 1) {
      const content = words.slice(0, index + 1).join(" ");
      setMessages((current) =>
        current.map((message) => (message.id === id ? { ...message, content } : message)),
      );
      await sleep(index < 60 ? 12 : 0);
    }
    setMessages((current) =>
      current.map((message) =>
        message.id === id ? { ...message, content: answer, citations } : message,
      ),
    );
  }

  async function selectConversation(id: string) {
    setError(null);
    setConversationId(id);
    const selected = conversations.find((conversation) => conversation.id === id);
    if (selected) {
      setLanguage(selected.language as SupportedLanguage);
      setSourceMode(selected.source_mode);
    }
    const history = await api.messages(id, token);
    setMessages(
      history.map((message) => ({
        ...message,
        role: message.role === "assistant" ? "assistant" : "user",
      })),
    );
    setMobileMenuOpen(false);
  }

  function newChat() {
    setConversationId(undefined);
    setMessages([]);
    setSourceMode(uploadSession ? "upload" : "official");
    setError(null);
    setMobileMenuOpen(false);
  }

  function uploaded(session: UploadSession) {
    setUploadSession(session);
    setSourceMode("upload");
    setMessages((current) => [
      ...current,
      {
        id: crypto.randomUUID(),
        role: "assistant",
        content: `PDF indexed for this session: ${session.filename}. Questions will use only this uploaded PDF while PDF mode is active.`,
        citations: [],
      },
    ]);
  }

  async function exportConversation(format: "pdf" | "txt") {
    if (!conversationId) {
      return;
    }
    const blob = await api.downloadExport(conversationId, format, token);
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${conversationId}.${format}`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  async function clearHistory() {
    await api.clearHistory(token);
    setMessages([]);
    setConversationId(undefined);
    await loadConversations();
  }

  return (
    <main className="flex h-screen overflow-hidden bg-fci-mist text-fci-ink dark:bg-[#0e1310] dark:text-white">
      <AppSidebar
        collapsed={sidebarCollapsed}
        onCollapsedChange={setSidebarCollapsed}
        conversations={conversations}
        recentCirculars={recentCirculars}
        activeConversationId={conversationId}
        language={language}
        onLanguageChange={setLanguage}
        onNewChat={newChat}
        onSelectConversation={selectConversation}
        onAsk={sendMessage}
        onSummarize={summarizeCircular}
        onOpenSettings={() => setSettingsOpen(true)}
      />

      {mobileMenuOpen ? (
        <div className="fixed inset-0 z-40 bg-black/35 lg:hidden">
          <div className="h-full w-[88vw] max-w-sm overflow-y-auto bg-white p-4 shadow-soft dark:bg-[#101712]">
            <div className="mb-4 flex items-center justify-between">
              <div className="font-semibold">FCI Assistant</div>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                aria-label="Close menu"
                onClick={() => setMobileMenuOpen(false)}
              >
                <X className="h-4 w-4" aria-hidden="true" />
              </Button>
            </div>
            <div className="space-y-3">
              <Button type="button" className="w-full" onClick={newChat}>
                <MessageSquarePlus className="h-4 w-4" aria-hidden="true" />
                New Chat
              </Button>
              {conversations.map((conversation) => (
                <button
                  key={conversation.id}
                  type="button"
                  onClick={() => selectConversation(conversation.id)}
                  className="block w-full rounded-lg px-3 py-2 text-left text-sm text-fci-steel hover:bg-fci-mist dark:text-white/70 dark:hover:bg-white/10"
                >
                  {conversation.title}
                </button>
              ))}
            </div>
          </div>
        </div>
      ) : null}

      <section className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-16 items-center justify-between border-b border-fci-line bg-white/75 px-4 backdrop-blur-xl dark:border-white/10 dark:bg-[#101712]/75 sm:px-6">
          <div className="flex min-w-0 items-center gap-3">
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="lg:hidden"
              aria-label="Open menu"
              onClick={() => setMobileMenuOpen(true)}
            >
              <Menu className="h-4 w-4" aria-hidden="true" />
            </Button>
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <h1 className="truncate text-sm font-semibold sm:text-base">
                  {conversationId ? "Circular Conversation" : "New Circular Chat"}
                </h1>
                <Badge>
                  <ShieldCheck className="h-3.5 w-3.5" aria-hidden="true" />
                  {sourceMode === "upload" ? "Uploaded PDF" : "Official FCI"}
                </Badge>
              </div>
              {uploadSession && sourceMode === "upload" ? (
                <p className="mt-1 truncate text-xs text-fci-steel dark:text-white/60">
                  {uploadSession.filename} expires {new Date(uploadSession.expires_at).toLocaleTimeString()}
                </p>
              ) : null}
            </div>
          </div>

          <div className="flex items-center gap-2">
            <div className="hidden sm:block">
              <LanguageSelector value={language} onChange={setLanguage} compact />
            </div>
            <Button
              type="button"
              variant="secondary"
              size="icon"
              aria-label="New chat"
              onClick={newChat}
            >
              <MessageSquarePlus className="h-4 w-4" aria-hidden="true" />
            </Button>
            <Button
              type="button"
              variant="secondary"
              size="icon"
              aria-label="Open settings"
              onClick={() => setSettingsOpen(true)}
            >
              <Settings className="h-4 w-4" aria-hidden="true" />
            </Button>
            {user ? (
              <Button type="button" variant="ghost" onClick={logout}>
                Sign out
              </Button>
            ) : (
              <Link
                href="/login"
                className="hidden h-10 items-center rounded-lg px-3 text-sm font-medium text-fci-primary hover:bg-fci-light dark:text-fci-light dark:hover:bg-white/10 sm:inline-flex"
              >
                Sign in
              </Link>
            )}
          </div>
        </header>

        <div className="grid min-h-0 flex-1 lg:grid-cols-[minmax(0,1fr)_340px]">
          <div className="flex min-w-0 flex-col">
            <div className="flex-1 overflow-y-auto px-4 py-6 sm:px-6">
              <div className="mx-auto flex max-w-4xl flex-col gap-5">
                {!messages.length ? (
                  <EmptyState onAsk={sendMessage} />
                ) : (
                  messages.map((message) => (
                    <MessageBubble key={message.id} message={message} fontScale={fontScale} />
                  ))
                )}
                {loading ? (
                  <div className="flex items-center gap-2 text-sm text-fci-steel dark:text-white/60">
                    <Loader2 className="h-4 w-4 animate-spin text-fci-primary" aria-hidden="true" />
                    Retrieving sources and drafting a grounded response
                  </div>
                ) : null}
                {error ? (
                  <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-400/20 dark:bg-red-400/10 dark:text-red-200">
                    {error}
                  </div>
                ) : null}
                <div ref={bottomRef} />
              </div>
            </div>

            <div className="border-t border-fci-line bg-fci-mist/95 px-4 py-4 backdrop-blur dark:border-white/10 dark:bg-[#0e1310]/95 sm:px-6">
              <div className="mx-auto max-w-4xl">
                <ChatComposer
                  disabled={loading}
                  token={token}
                  onSend={sendMessage}
                  onUploaded={uploaded}
                />
              </div>
            </div>
          </div>

          <aside className="hidden border-l border-fci-line bg-white/70 p-4 backdrop-blur-xl dark:border-white/10 dark:bg-[#101712]/75 lg:block">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="flex items-center gap-2 text-sm font-semibold text-fci-ink dark:text-white">
                <PanelRightOpen className="h-4 w-4 text-fci-primary" aria-hidden="true" />
                Sources
              </h2>
              <Badge>{latestCitations.length}</Badge>
            </div>
            <div className="space-y-3">
              {latestCitations.length ? (
                latestCitations.map((citation) => (
                  <CitationCard key={`${citation.source_id}-${citation.title}`} citation={citation} />
                ))
              ) : (
                <div className="rounded-lg border border-dashed border-fci-line p-4 text-sm leading-6 text-fci-steel dark:border-white/10 dark:text-white/60">
                  Citations appear here after an answer is supported by retrieved sources.
                </div>
              )}
            </div>
          </aside>
        </div>
      </section>

      <SettingsPanel
        open={settingsOpen}
        onOpenChange={setSettingsOpen}
        language={language}
        onLanguageChange={setLanguage}
        fontScale={fontScale}
        onFontScaleChange={setFontScale}
        canExport={Boolean(conversationId)}
        onExport={exportConversation}
        onClearHistory={clearHistory}
      />
    </main>
  );
}

function EmptyState({ onAsk }: { onAsk: (question: string) => void }) {
  return (
    <div className="mx-auto flex min-h-[58vh] max-w-3xl flex-col justify-center text-center">
      <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-lg bg-fci-primary text-white shadow-crisp">
        <Search className="h-6 w-6" aria-hidden="true" />
      </div>
      <h2 className="mt-6 text-3xl font-semibold tracking-normal text-fci-ink dark:text-white">
        Start with an official circular question
      </h2>
      <p className="mt-3 text-sm leading-6 text-fci-steel dark:text-white/70">
        The assistant retrieves circular excerpts first, then answers with citations.
      </p>
      <div className="mt-7 grid gap-2 sm:grid-cols-2">
        {suggestions.map((suggestion) => (
          <button
            key={suggestion}
            type="button"
            onClick={() => onAsk(suggestion)}
            className="rounded-lg border border-fci-line bg-white px-4 py-3 text-left text-sm font-medium text-fci-ink transition hover:border-fci-primary/40 hover:bg-fci-light dark:border-white/10 dark:bg-white/10 dark:text-white dark:hover:bg-white/10"
          >
            {suggestion}
          </button>
        ))}
      </div>
    </div>
  );
}

function sleep(ms: number) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}
