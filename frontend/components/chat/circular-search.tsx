"use client";

import { useInterface } from "@/contexts/interface-context";
import { FormEvent, useState } from "react";
import { ExternalLink, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { api } from "@/lib/api";
import type { Circular } from "@/lib/types";
import { BookmarkButton } from "@/components/chat/bookmarks";

type CircularSearchProps = {
  onAsk: (question: string) => void;
  onSummarize: (circularId: string, style: "short" | "detailed" | "bullets") => void;
};

export function CircularSearch({ onAsk, onSummarize }: CircularSearchProps) {
  const t = useInterface();
  const [query, setQuery] = useState("");
  const [circularNumber, setCircularNumber] = useState("");
  const [department, setDepartment] = useState("");
  const [topic, setTopic] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [summaryStyle, setSummaryStyle] = useState<"short" | "detailed" | "bullets">("short");
  const [items, setItems] = useState<Circular[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);
  const [total, setTotal] = useState(0);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const params = new URLSearchParams();
    if (query.trim()) {
      params.set("query", query.trim());
    }
    if (circularNumber.trim()) {
      params.set("circular_number", circularNumber.trim());
    }
    if (department.trim()) {
      params.set("department", department.trim());
    }
    if (topic.trim()) {
      params.set("topic", topic.trim());
    }
    if (startDate) {
      params.set("start_date", startDate);
    }
    if (endDate) {
      params.set("end_date", endDate);
    }
    params.set("limit", "8");
    setLoading(true);
    setError(null);
    try {
      if (startDate && endDate && startDate > endDate) throw new Error("Start date must be before end date.");
      const response = await api.searchCirculars(params);
      setItems(response.items);
      setTotal(response.total);
      setSearched(true);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Search failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-3">
      <form onSubmit={submit} className="flex gap-2">
        <Input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder={t("Search circulars")}
          className="h-10"
        />
        <Button type="submit" size="icon" variant="secondary" aria-label={t("Search circulars")}>
          <Search className="h-4 w-4" aria-hidden="true" />
        </Button>
      </form>

      <details className="rounded-lg border border-fci-line bg-white p-3 dark:border-white/10 dark:bg-white/10">
        <summary className="cursor-pointer text-sm font-medium text-fci-ink dark:text-white">
          {t("Filters")}
        </summary>
        <div className="mt-3 grid gap-2">
          <Input
            value={circularNumber}
            onChange={(event) => setCircularNumber(event.target.value)}
            placeholder={t("Circular number")}
            className="h-10"
          />
          <Input
            value={department}
            onChange={(event) => setDepartment(event.target.value)}
            placeholder={t("Department")}
            className="h-10"
          />
          <Input
            value={topic}
            onChange={(event) => setTopic(event.target.value)}
            placeholder={t("Topic")}
            className="h-10"
          />
          <div className="grid grid-cols-2 gap-2">
            <Input
              value={startDate}
              onChange={(event) => setStartDate(event.target.value)}
              type="date"
              aria-label={t("Start date")}
              className="h-10"
            />
            <Input
              value={endDate}
              onChange={(event) => setEndDate(event.target.value)}
              type="date"
              aria-label={t("End date")}
              className="h-10"
            />
          </div>
          <Select
            label={t("Summary style")}
            value={summaryStyle}
            onChange={(value) => setSummaryStyle(value as "short" | "detailed" | "bullets")}
            options={["short", "detailed", "bullets"]}
            optionLabels={{ short: t("Short"), detailed: t("Detailed"), bullets: t("Bullet points") }}
          />
        </div>
      </details>

      <div className="space-y-2">
        {error ? <p role="alert" className="text-xs text-red-600">{error}</p> : null}
        {searched && !loading ? <p className="text-xs text-fci-steel">{total} circulars found</p> : null}
        {loading ? (
          <div className="h-20 animate-pulse rounded-lg bg-fci-light dark:bg-white/10" />
        ) : null}
        {items.map((item) => (
          <article
            key={item.id}
            className="rounded-lg border border-fci-line bg-white p-3 text-sm dark:border-white/10 dark:bg-white/10"
          >
            <div className="line-clamp-2 font-medium text-fci-ink dark:text-white">
              {item.title}
            </div>
            <div className="mt-1 text-xs text-fci-steel dark:text-white/60">
              {item.circular_number || "No number"} | {item.publication_date || "No date"}
            </div>
            <div className="mt-3 flex flex-wrap items-center gap-1">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => onSummarize(item.id, summaryStyle)}
              >
                {t("Summarize")}
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => onAsk(`What are the key points in ${item.circular_number || item.title}?`)}
              >
                {t("Ask")}
              </Button>
              <a
                href={item.official_url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex h-9 items-center gap-1 rounded-lg px-3 text-sm font-medium text-fci-primary hover:bg-fci-light dark:text-fci-light dark:hover:bg-white/10"
              >
                <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
                {t("Open")}
              </a>
              <BookmarkButton circular={item} />
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
