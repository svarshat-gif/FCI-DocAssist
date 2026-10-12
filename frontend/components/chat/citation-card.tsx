"use client";

import { useInterface } from "@/contexts/interface-context";
import { ExternalLink, FileText } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { Citation } from "@/lib/types";

export function CitationCard({ citation }: { citation: Citation }) {
  const t = useInterface();
  const href = citation.official_url === "temporary-upload" ? undefined : citation.official_url;

  return (
    <article className="rounded-lg border border-fci-line bg-white p-4 shadow-sm dark:border-white/10 dark:bg-white/10">
      <div className="flex items-start gap-3">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-fci-light text-fci-primary dark:bg-fci-primary/20">
          <FileText className="h-4 w-4" aria-hidden="true" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap gap-2">
            <Badge>{citation.source_id}</Badge>
            {citation.page_number ? <Badge>{t("Page")} {citation.page_number}</Badge> : null}
          </div>
          <h4 className="mt-3 line-clamp-2 text-sm font-semibold text-fci-ink dark:text-white">
            {citation.title}
          </h4>
          <p className="mt-1 text-xs leading-5 text-fci-steel dark:text-white/70">
            {citation.circular_number || "Circular number unavailable"}
            {citation.publication_date ? ` | ${citation.publication_date}` : ""}
          </p>
          <p className="mt-3 line-clamp-3 text-sm leading-6 text-fci-steel dark:text-white/70">
            {citation.snippet}
          </p>
          {href ? (
            <a
              className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-fci-primary hover:text-fci-dark dark:text-fci-light"
              href={href}
              target="_blank"
              rel="noreferrer"
            >
              {t("Official source")}
              <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
            </a>
          ) : null}
        </div>
      </div>
    </article>
  );
}
