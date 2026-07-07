"use client";

import { motion } from "framer-motion";
import {
  Bot,
  CalendarSync,
  FileUp,
  Languages,
  MessageSquareText,
  Quote,
} from "lucide-react";

const features = [
  {
    icon: Bot,
    title: "Grounded AI Chat",
    copy: "Answers are generated only after retrieving indexed circular excerpts.",
  },
  {
    icon: Quote,
    title: "Citation Cards",
    copy: "Each supported answer carries circular number, title, date, URL, and page.",
  },
  {
    icon: CalendarSync,
    title: "Daily Updates",
    copy: "The crawler fingerprints new PDFs and skips duplicates automatically.",
  },
  {
    icon: FileUp,
    title: "Temporary PDF Mode",
    copy: "Uploaded PDFs are embedded for the session and removed after expiry.",
  },
  {
    icon: Languages,
    title: "Multilingual Responses",
    copy: "Gemini returns answers in the selected language without translation APIs.",
  },
  {
    icon: MessageSquareText,
    title: "Conversation Memory",
    copy: "Follow-up questions use recent chat context for references like 'it'.",
  },
];

export function FeatureGrid() {
  return (
    <section className="bg-white px-5 py-16 dark:bg-[#101712] sm:px-8 lg:px-10">
      <div className="mx-auto max-w-7xl">
        <div className="mb-9 flex flex-col justify-between gap-5 md:flex-row md:items-end">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-fci-primary">
              Built for official answers
            </p>
            <h2 className="mt-3 max-w-2xl text-3xl font-semibold tracking-normal text-fci-ink dark:text-white sm:text-4xl">
              A complete circular intelligence workspace
            </h2>
          </div>
          <p className="max-w-xl text-sm leading-6 text-fci-steel dark:text-white/70">
            Designed for repeated employee workflows: search, compare, summarize,
            ask follow-ups, upload a reference PDF, and export the conversation.
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {features.map((feature, index) => (
            <motion.article
              key={feature.title}
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-80px" }}
              transition={{ duration: 0.4, delay: index * 0.04 }}
              className="rounded-lg border border-fci-line bg-fci-mist/70 p-5 shadow-sm transition hover:-translate-y-1 hover:border-fci-primary/30 hover:shadow-crisp dark:border-white/10 dark:bg-white/10"
            >
              <feature.icon className="h-5 w-5 text-fci-primary" aria-hidden="true" />
              <h3 className="mt-5 text-lg font-semibold text-fci-ink dark:text-white">
                {feature.title}
              </h3>
              <p className="mt-2 text-sm leading-6 text-fci-steel dark:text-white/70">
                {feature.copy}
              </p>
            </motion.article>
          ))}
        </div>
      </div>
    </section>
  );
}
