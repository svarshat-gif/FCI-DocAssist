"use client";

import { FormEvent, useState } from "react";
import { ExternalLink, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { api } from "@/lib/api";
import type { Circular } from "@/lib/types";

type CircularSearchProps = {
  onAsk: (question: string) => void;
  onSummarize: (circularId: string, style: "short" | "detailed" | "bullets") => void;
};

export function CircularSearch({ onAsk, onSummarize }: CircularSearchProps) {
  const [query, setQuery] = useState("");
  const [circularNumber, setCircularNumber] = useState("");
  const [department, setDepartment] = useState("");
  const [topic, setTopic] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [summaryStyle, setSummaryStyle] = useState<"short" | "detailed" | "bullets">("short");
  const [items, setItems] = useState<Circular[]>([]);
  const [loading, setLoading] = useState(false);

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
    try {
      const response = await api.searchCirculars(params);
      setItems(response.items);
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
          placeholder="Search circulars"
          className="h-10"
        />
        <Button type="submit" size="icon" variant="secondary" aria-label="Search circulars">
          <Search className="h-4 w-4" aria-hidden="true" />
        </Button>
      </form>

      <details className="rounded-lg border border-fci-line bg-white p-3 dark:border-white/10 dark:bg-white/10">
        <summary className="cursor-pointer text-sm font-medium text-fci-ink dark:text-white">
          Filters
        </summary>
        <div className="mt-3 grid gap-2">
          <Input
            value={circularNumber}
            onChange={(event) => setCircularNumber(event.target.value)}
            placeholder="Circular number"
            className="h-10"
          />
          <Input
            value={department}
            onChange={(event) => setDepartment(event.target.value)}
            placeholder="Department"
            className="h-10"
          />
          <Input
            value={topic}
            onChange={(event) => setTopic(event.target.value)}
            placeholder="Topic"
            className="h-10"
          />
          <div className="grid grid-cols-2 gap-2">
            <Input
              value={startDate}
              onChange={(event) => setStartDate(event.target.value)}
              type="date"
              aria-label="Start date"
              className="h-10"
            />
            <Input
              value={endDate}
              onChange={(event) => setEndDate(event.target.value)}
              type="date"
              aria-label="End date"
              className="h-10"
            />
          </div>
          <Select
            label="Summary style"
            value={summaryStyle}
            onChange={(value) => setSummaryStyle(value as "short" | "detailed" | "bullets")}
            options={["short", "detailed", "bullets"]}
          />
        </div>
      </details>

      <div className="space-y-2">
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
            <div className="mt-3 flex gap-2">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => onSummarize(item.id, summaryStyle)}
              >
                Summarize
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => onAsk(`What are the key points in ${item.circular_number || item.title}?`)}
              >
                Ask
              </Button>
              <a
                href={item.official_url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex h-9 items-center gap-1 rounded-lg px-3 text-sm font-medium text-fci-primary hover:bg-fci-light dark:text-fci-light dark:hover:bg-white/10"
              >
                <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
                Open
              </a>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
