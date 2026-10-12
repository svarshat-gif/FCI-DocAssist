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
    title: "Ask About Circulars",
    copy: "Clear answers based on official FCI documents.",
  },
  {
    icon: Quote,
    title: "Check the Original",
    copy: "Open the circular and relevant page behind an answer.",
  },
  {
    icon: CalendarSync,
    title: "Daily Updates",
    copy: "Keep up with newly published circulars without searching each day.",
  },
  {
    icon: FileUp,
    title: "Your PDF Documents",
    copy: "Ask about an uploaded PDF for up to an hour. Saved chats remain in your history.",
  },
  {
    icon: Languages,
    title: "Your Language",
    copy: "Read and ask questions in your preferred language.",
  },
  {
    icon: MessageSquareText,
    title: "Previous Chats",
    copy: "Return to saved conversations and continue where you left off.",
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
              Your FCI documents, in one place
            </h2>
          </div>
          <p className="max-w-xl text-sm leading-6 text-fci-steel dark:text-white/70">
            From a quick question to a detailed summary, keep the information
            you need close at hand.
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
