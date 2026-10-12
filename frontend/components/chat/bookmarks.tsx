"use client";

import { useState } from "react";
import { Bookmark, BookmarkCheck, ExternalLink, MessageSquare } from "lucide-react";
import { useLibrary } from "@/contexts/library-context";
import { Button } from "@/components/ui/button";
import type { Circular } from "@/lib/types";
import { useInterface } from "@/contexts/interface-context";

export function BookmarkButton({ circular }: { circular: Circular }) {
  const { bookmarks, toggle } = useLibrary();
  const saved = bookmarks.some((item) => item.id === circular.id);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  return <span className="inline-flex flex-col">
    <Button variant="ghost" size="icon" aria-label={saved ? "Remove bookmark" : "Bookmark circular"} aria-pressed={saved} disabled={busy} onClick={async () => {
      setBusy(true); setError(null);
      try { await toggle(circular); } catch (caught) { setError(caught instanceof Error ? caught.message : "Could not update bookmark."); } finally { setBusy(false); }
    }}>{saved ? <BookmarkCheck className="h-4 w-4 text-fci-primary" /> : <Bookmark className="h-4 w-4" />}</Button>
    {error ? <span role="alert" className="text-xs text-red-600">{error}</span> : null}
  </span>;
}

export function BookmarkPanel({ onAsk }: { onAsk: (question: string) => void }) {
  const t = useInterface();
  const { bookmarks } = useLibrary();
  return <div className="space-y-2">
    {!bookmarks.length ? <p className="text-sm text-fci-steel dark:text-white/60">{t("No saved circulars.")}</p> : null}
    {bookmarks.map((item) => <article key={item.id} className="border-b border-fci-line py-2 dark:border-white/10">
      <p className="line-clamp-2 text-sm font-medium">{item.title}</p>
      <div className="mt-2 flex items-center gap-1">
        <Button variant="ghost" size="icon" aria-label="Ask about circular" onClick={() => onAsk(`What are the key points in ${item.circular_number || item.title}?`)}><MessageSquare className="h-4 w-4" /></Button>
        <a href={item.official_url} target="_blank" rel="noreferrer" title="Open circular" aria-label="Open circular" className="inline-flex h-10 w-10 items-center justify-center"><ExternalLink className="h-4 w-4" /></a>
        <BookmarkButton circular={item} />
      </div>
    </article>)}
  </div>;
}
