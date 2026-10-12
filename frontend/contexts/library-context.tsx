"use client";

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { useAuth } from "@/contexts/auth-context";
import { api } from "@/lib/api";
import type { Circular } from "@/lib/types";

type Library = { bookmarks: Circular[]; toggle: (circular: Circular) => Promise<void> };
const LibraryContext = createContext<Library | null>(null);

export function LibraryProvider({ children }: { children: ReactNode }) {
  const { token } = useAuth();
  const [bookmarks, setBookmarks] = useState<Circular[]>([]);
  useEffect(() => {
    let active = true;
    setBookmarks([]);
    if (token) api.bookmarks(token).then((items) => { if (active) setBookmarks(items); }).catch(() => {});
    return () => { active = false; };
  }, [token]);
  const toggle = useCallback(async (circular: Circular) => {
    if (!token) throw new Error("Sign in to save circulars.");
    const saved = bookmarks.some((item) => item.id === circular.id);
    await api.bookmark(circular.id, !saved, token);
    setBookmarks((items) => saved ? items.filter((item) => item.id !== circular.id) : [circular, ...items.filter((item) => item.id !== circular.id)]);
  }, [bookmarks, token]);
  return <LibraryContext.Provider value={{ bookmarks, toggle }}>{children}</LibraryContext.Provider>;
}

export function useLibrary() {
  const library = useContext(LibraryContext);
  if (!library) throw new Error("LibraryProvider is required.");
  return library;
}
