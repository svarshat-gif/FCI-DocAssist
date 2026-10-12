"use client";

import { useRouter, useSearchParams } from "next/navigation";
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
import { ChatHistory } from "@/components/chat/chat-history";
import { CitationCard } from "@/components/chat/citation-card";
import { LanguageSelector } from "@/components/chat/language-selector";
import { MessageBubble } from "@/components/chat/message-bubble";
import { SettingsPanel } from "@/components/chat/settings-panel";
import { CircularSearch } from "@/components/chat/circular-search";
import { BookmarkPanel } from "@/components/chat/bookmarks";
import { LibraryProvider } from "@/contexts/library-context";
import { InterfaceProvider, useInterface } from "@/contexts/interface-context";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/contexts/auth-context";
import { api } from "@/lib/api";
import type { SupportedLanguage } from "@/lib/languages";
import type { ChatMessage, Circular, Citation, Conversation, UploadSession } from "@/lib/types";

const suggestions = [
  "What is the transfer policy?",
  "Which circular mentions maternity leave?",
  "Summarize Circular 18/2024",
  "What does the promotion circular say?",
];

export function ChatShell() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { token, user, logout, loading: authLoading } = useAuth();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversationId, setConversationId] = useState<string | undefined>();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeTitle, setActiveTitle] = useState<string>();
  const [historyQuery, setHistoryQuery] = useState("");
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [hasMoreHistory, setHasMoreHistory] = useState(false);
  const historyRequest = useRef(0);
  const restoredChat = useRef<string | undefined>(undefined);
  const [recentCirculars, setRecentCirculars] = useState<Circular[]>([]);
  const [language, setLanguage] = useState<SupportedLanguage>("English");
  const t = useInterface(language);
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
  const requestActive = useRef(false);
  const preferencesReady = useRef(false);

  useEffect(() => {
    if (!uploadSession || !token) return;
    const release = () => { void api.deleteUpload(uploadSession.id, token).catch(() => undefined); };
    const expire = window.setTimeout(() => setUploadSession(null), Math.max(0, new Date(uploadSession.expires_at).getTime() - Date.now()));
    window.addEventListener("pagehide", release);
    return () => {
      window.clearTimeout(expire);
      window.removeEventListener("pagehide", release);
      release();
    };
  }, [uploadSession, token]);

  useEffect(() => {
    setConversationId(undefined);
    setMessages([]);
    setUploadSession(null);
    setSourceMode("official");
    setConversations([]);
    setActiveTitle(undefined);
    setHistoryQuery("");
    restoredChat.current = undefined;
    historyRequest.current += 1;
  }, [token]);

  useEffect(() => {
    const saved = window.localStorage.getItem("fci-preferences");
    if (saved) {
      try {
        const preferences = JSON.parse(saved);
        if (["English", "Hindi", "Kannada", "Telugu", "Tamil", "Malayalam", "Marathi", "Gujarati", "Bengali", "Punjabi"].includes(preferences.language)) setLanguage(preferences.language);
        if (typeof preferences.fontScale === "number") setFontScale(Math.min(1.2, Math.max(0.9, preferences.fontScale)));
      } catch { /* Ignore invalid browser preferences. */ }
    }
    preferencesReady.current = true;
  }, []);

  useEffect(() => {
    if (preferencesReady.current) window.localStorage.setItem("fci-preferences", JSON.stringify({ language, fontScale }));
  }, [language, fontScale]);

  const latestCitations = useMemo<Citation[]>(() => {
    return [...messages].reverse().find((message) => message.citations?.length)?.citations ?? [];
  }, [messages]);

  const loadConversations = useCallback(async () => {
    const requestId = ++historyRequest.current;
    if (!token) { setConversations([]); setHasMoreHistory(false); setHistoryLoading(false); setHistoryError(null); return; }
    setHistoryLoading(true);
    setHistoryError(null);
    try {
      const items = await api.conversations(token, historyQuery);
      if (requestId !== historyRequest.current) return;
      setConversations(items);
      setHasMoreHistory(items.length === 50);
    } catch { if (requestId === historyRequest.current) setHistoryError("Your chats could not be loaded."); }
    finally { if (requestId === historyRequest.current) setHistoryLoading(false); }
  }, [token, historyQuery]);

  async function loadOlderChats() {
    if (!token || historyLoading) return;
    const requestId = ++historyRequest.current;
    setHistoryLoading(true);
    setHistoryError(null);
    try {
      const items = await api.conversations(token, historyQuery, conversations.length);
      if (requestId !== historyRequest.current) return;
      setConversations((current) => [...current, ...items.filter((item) => !current.some((existing) => existing.id === item.id))]);
      setHasMoreHistory(items.length === 50);
    } catch { if (requestId === historyRequest.current) setHistoryError("Older chats could not be loaded."); }
    finally { if (requestId === historyRequest.current) setHistoryLoading(false); }
  }

  useEffect(() => {
    const timer = window.setTimeout(loadConversations, 250);
    return () => { window.clearTimeout(timer); historyRequest.current += 1; };
  }, [loadConversations]);

  useEffect(() => {
    api.recentCirculars().then(setRecentCirculars).catch(() => setRecentCirculars([]));
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, loading]);

  const sendMessage = useCallback(
    async (content: string) => {
      if (authLoading || requestActive.current) {
        return;
      }
      if (!token) {
        window.sessionStorage.setItem("fci-pending-prompt", content);
        router.push("/login");
        return;
      }
      requestActive.current = true;
      setError(null);
      const userMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: "user",
        content,
      };
      setMessages((current) => [...current, userMessage]);
      setLoading(true);
      const assistantId = crypto.randomUUID();
      setMessages((current) => [...current, { id: assistantId, role: "assistant", content: "", citations: [] }]);

      try {
        const response = await api.chatStream(
          {
            message: content,
            conversation_id: conversationId,
            language,
            source_mode: sourceMode,
            upload_session_id: sourceMode === "upload" ? uploadSession?.id : undefined,
          },
          (content, citations) => setMessages((current) => current.map((message) => message.id === assistantId ? { ...message, content, citations } : message)),
          token,
        );
        setConversationId(response.conversation_id);
        restoredChat.current = response.conversation_id;
        setActiveTitle((current) => current || content.slice(0, 70));
        router.replace(`/chat?conversation=${encodeURIComponent(response.conversation_id)}`, { scroll: false });
        setMessages((current) => current.map((message) => message.id === assistantId ? { ...message, content: response.answer, citations: response.citations } : message));
        await loadConversations();
      } catch (caught) {
        const message = caught instanceof Error ? caught.message : "Unable to answer right now.";
        setError(message);
        setMessages((current) => current.filter((item) => item.id !== assistantId));
      } finally {
        requestActive.current = false;
        setLoading(false);
      }
    },
    [
      conversationId,
      language,
      loadConversations,
      sourceMode,
      token,
      uploadSession?.id,
      authLoading,
      router,
    ],
  );

  const summarizeCircular = useCallback(
    async (circularId: string, style: "short" | "detailed" | "bullets") => {
      if (requestActive.current) {
        return;
      }
      if (!token) { router.push("/login"); return; }
      requestActive.current = true;
      setError(null);
      setLoading(true);
      setConversationId(undefined);
      setMessages([
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
        setConversationId(response.conversation_id);
        restoredChat.current = response.conversation_id;
        setActiveTitle("Circular summary");
        router.replace(`/chat?conversation=${encodeURIComponent(response.conversation_id)}`, { scroll: false });
        setSourceMode("official");
        setUploadSession(null);
        setMessages((current) => [...current, { id: crypto.randomUUID(), role: "assistant", content: response.summary, citations: response.citations }]);
        await loadConversations();
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : "Unable to summarize circular.");
      } finally {
        requestActive.current = false;
        setLoading(false);
      }
    },
    [language, token, router, loadConversations],
  );

  useEffect(() => {
    if (authLoading) return;
    const prompt = searchParams.get("prompt") || window.sessionStorage.getItem("fci-pending-prompt");
    if (prompt && !consumedInitialPrompt.current) {
      consumedInitialPrompt.current = true;
      window.sessionStorage.removeItem("fci-pending-prompt");
      sendMessage(prompt);
    }
  }, [searchParams, sendMessage, authLoading]);

  const selectConversation = useCallback(async (id: string) => {
    if (requestActive.current || id === conversationId) return;
    restoredChat.current = id;
    requestActive.current = true;
    setLoading(true);
    try {
      setError(null);
      const [history, selected] = await Promise.all([api.messages(id, token), api.conversation(id, token)]);
      setConversationId(id);
      setActiveTitle(selected.title);
      setUploadSession(null);
      if (selected) {
        setLanguage(selected.language as SupportedLanguage);
        setSourceMode(selected.source_mode);
        if (selected.upload_session_id) {
          try { setUploadSession(await api.uploadSession(selected.upload_session_id, token)); }
          catch { setError("This PDF session has expired. Upload it again to continue asking questions."); }
        }
      }
      setMessages(history.map((message) => ({ ...message, role: message.role === "assistant" ? "assistant" : "user" })));
      setMobileMenuOpen(false);
      router.replace(`/chat?conversation=${encodeURIComponent(id)}`, { scroll: false });
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Unable to load conversation."); }
    finally { requestActive.current = false; setLoading(false); }
  }, [token, router, conversationId]);

  useEffect(() => {
    const id = searchParams.get("conversation");
    if (!id) { restoredChat.current = undefined; return; }
    if (authLoading || !token || restoredChat.current === id || requestActive.current) return;
    restoredChat.current = id;
    void selectConversation(id);
  }, [authLoading, token, searchParams, selectConversation]);

  function newChat() {
    if (requestActive.current) return;
    setConversationId(undefined);
    setActiveTitle(undefined);
    setMessages([]);
    setSourceMode("official");
    setUploadSession(null);
    setError(null);
    setMobileMenuOpen(false);
    router.replace("/chat", { scroll: false });
  }

  function uploaded(session: UploadSession) {
    if (requestActive.current) return;
    setConversationId(undefined);
    setActiveTitle(undefined);
    setUploadSession(session);
    setSourceMode("upload");
    setMessages([]);
    router.replace("/chat", { scroll: false });
  }

  async function exportConversation(format: "pdf" | "txt") {
    if (!conversationId) {
      return;
    }
    try {
    const blob = await api.downloadExport(conversationId, format, token);
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${conversationId}.${format}`;
    anchor.click();
    URL.revokeObjectURL(url);
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Export failed."); }
  }

  async function clearHistory() {
    if (requestActive.current || !window.confirm("Delete all your conversation history?")) return;
    try {
    await api.clearHistory(token);
    setMessages([]);
    setConversationId(undefined);
    setActiveTitle(undefined);
    setSourceMode("official");
    setUploadSession(null);
    router.replace("/chat", { scroll: false });
    await loadConversations();
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Unable to clear history."); }
  }

  const historyProps = {
    conversations, activeConversationId: conversationId, query: historyQuery,
    onQueryChange: (query: string) => {
      historyRequest.current += 1;
      setHistoryQuery(query);
      setConversations([]);
      setHasMoreHistory(false);
      setHistoryError(null);
      setHistoryLoading(Boolean(token));
    }, onSelectConversation: selectConversation,
    onLoadMore: loadOlderChats, onRetry: loadConversations, hasMore: hasMoreHistory,
    loading: historyLoading, error: historyError, signedIn: Boolean(token), disabled: loading,
  };

  return (
    <InterfaceProvider language={language}><LibraryProvider>
    <main className="flex h-dvh overflow-hidden bg-fci-mist text-fci-ink dark:bg-[#0e1310] dark:text-white">
      <AppSidebar
        collapsed={sidebarCollapsed}
        onCollapsedChange={setSidebarCollapsed}
        history={historyProps}
        recentCirculars={recentCirculars}
        language={language}
        onLanguageChange={setLanguage}
        onNewChat={newChat}
        onAsk={sendMessage}
        onSummarize={summarizeCircular}
        onOpenSettings={() => setSettingsOpen(true)}
      />

      {mobileMenuOpen ? (
        <div className="fixed inset-0 z-40 bg-black/35 lg:hidden">
          <div className="h-full w-[88vw] max-w-sm overflow-y-auto bg-white p-4 shadow-soft dark:bg-[#101712]">
            <div className="mb-4 flex items-center justify-between">
              <div className="font-semibold">FCI Doc Assist</div>
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
                {t("New chat")}
              </Button>
              <ChatHistory {...historyProps} />
              <LanguageSelector value={language} onChange={setLanguage} />
              <CircularSearch onAsk={sendMessage} onSummarize={summarizeCircular} />
              <BookmarkPanel onAsk={sendMessage} />
              {!user ? <Link href="/login" className="block text-sm text-fci-primary">{t("Sign in")}</Link> : null}
              {user ? <Button variant="ghost" disabled={loading} onClick={logout}>{t("Sign out")}</Button> : null}
            </div>
          </div>
        </div>
      ) : null}

      <section className="flex min-w-0 flex-1 flex-col">
        <header className="flex min-h-16 shrink-0 items-center justify-between gap-2 border-b border-fci-line bg-white/75 px-4 py-2 backdrop-blur-xl dark:border-white/10 dark:bg-[#101712]/75 sm:px-6">
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
              <div className="flex min-w-0 flex-wrap items-center gap-2">
                <h1 className="max-w-full truncate text-sm font-semibold sm:text-base">
                  {activeTitle || t("New chat")}
                </h1>
                <Badge className="max-w-full whitespace-normal break-words">
                  <ShieldCheck className="h-3.5 w-3.5" aria-hidden="true" />
                  {sourceMode === "upload" ? t("Uploaded PDF") : t("Official FCI")}
                </Badge>
              </div>
              {uploadSession && sourceMode === "upload" ? (
                <p className="mt-1 truncate text-xs text-fci-steel dark:text-white/60">
                  {uploadSession.filename} expires {new Date(uploadSession.expires_at).toLocaleTimeString()}
                </p>
              ) : null}
            </div>
          </div>

          <div className="flex shrink-0 items-center gap-2">
            {uploadSession ? (
              <Button type="button" variant="secondary" size="icon" disabled={loading} aria-label="End PDF chat" title="End PDF chat" onClick={newChat}>
                <X className="h-4 w-4" aria-hidden="true" />
              </Button>
            ) : null}
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
              <Button type="button" variant="ghost" className="hidden sm:inline-flex" disabled={loading} onClick={logout}>
                {t("Sign out")}
              </Button>
            ) : (
              <Link
                href="/login"
                className="hidden h-10 items-center rounded-lg px-3 text-sm font-medium text-fci-primary hover:bg-fci-light dark:text-fci-light dark:hover:bg-white/10 sm:inline-flex"
              >
                {t("Sign in")}
              </Link>
            )}
          </div>
        </header>

        <div className="grid min-h-0 flex-1 lg:grid-cols-[minmax(0,1fr)_340px]">
          <div className="flex min-h-0 min-w-0 flex-col">
            <div className="min-h-0 flex-1 overflow-y-auto px-4 py-6 sm:px-6">
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
                    {t("Searching circulars…")}
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
                  busy={loading || authLoading}
                  disabled={loading || authLoading || !token || (sourceMode === "upload" && !uploadSession)}
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
                {t("Sources")}
              </h2>
              <Badge>{latestCitations.length}</Badge>
            </div>
            <div className="space-y-3">
              {latestCitations.length ? (
                latestCitations.map((citation) => (
                  <CitationCard key={`${citation.source_id}-${citation.title}`} citation={citation} />
                ))
              ) : (
                <div className="border-b border-fci-line py-4 text-sm text-fci-steel dark:border-white/10 dark:text-white/60">0</div>
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
    </LibraryProvider></InterfaceProvider>
  );
}

function EmptyState({ onAsk }: { onAsk: (question: string) => void }) {
  const t = useInterface();
  return (
    <div className="mx-auto flex min-h-[58vh] max-w-3xl flex-col justify-center text-center">
      <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-lg bg-fci-primary text-white shadow-crisp">
        <Search className="h-6 w-6" aria-hidden="true" />
      </div>
      <h2 className="mt-6 text-3xl font-semibold tracking-normal text-fci-ink dark:text-white">
        {t("What would you like to know?")}
      </h2>
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

