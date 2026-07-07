"use client";

import Image from "next/image";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { motion } from "framer-motion";
import { ArrowRight, CheckCircle2, FileSearch, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";

export function Hero() {
  const router = useRouter();
  const [prompt, setPrompt] = useState("");

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const query = prompt.trim();
    router.push(query ? `/chat?prompt=${encodeURIComponent(query)}` : "/chat");
  }

  return (
    <section className="relative flex min-h-[86vh] items-center overflow-hidden bg-fci-mist">
      <Image
        src="/fci-ai-assistant-hero.png"
        alt="AI assistant interface reviewing official document citations"
        fill
        priority
        className="object-cover"
      />
      <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(247,250,248,0.94)_0%,rgba(247,250,248,0.82)_36%,rgba(247,250,248,0.24)_100%)] dark:bg-[linear-gradient(90deg,rgba(14,19,16,0.94)_0%,rgba(14,19,16,0.78)_42%,rgba(14,19,16,0.32)_100%)]" />
      <div className="surface-grid absolute inset-0 opacity-30" />

      <div className="relative mx-auto flex w-full max-w-7xl flex-col px-5 py-20 sm:px-8 lg:px-10">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.65, ease: "easeOut" }}
          className="max-w-3xl"
        >
          <div className="mb-5 inline-flex items-center gap-2 rounded-lg border border-fci-primary/20 bg-white/80 px-3 py-2 text-sm font-medium text-fci-dark shadow-crisp backdrop-blur dark:border-white/10 dark:bg-white/10 dark:text-fci-light">
            <ShieldCheck className="h-4 w-4" aria-hidden="true" />
            Official circular citations required
          </div>
          <h1 className="text-5xl font-semibold tracking-normal text-fci-ink dark:text-white sm:text-6xl lg:text-7xl">
            Ask Anything About FCI Circulars
          </h1>
          <p className="mt-6 max-w-2xl text-lg leading-8 text-fci-steel dark:text-white/75">
            Search, summarize, and chat with indexed Food Corporation of India circulars
            through a grounded RAG assistant that refuses unsupported answers.
          </p>

          <form
            onSubmit={submit}
            className="mt-9 flex max-w-2xl items-center gap-2 rounded-lg border border-white/70 bg-white/90 p-2 shadow-soft backdrop-blur-xl dark:border-white/10 dark:bg-white/10"
          >
            <FileSearch className="ml-3 h-5 w-5 shrink-0 text-fci-primary" aria-hidden="true" />
            <input
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
              className="h-12 min-w-0 flex-1 bg-transparent text-base text-fci-ink outline-none placeholder:text-fci-steel/60 dark:text-white"
              placeholder="Summarize Circular 18/2024"
              aria-label="Ask about FCI circulars"
            />
            <Button type="submit" className="shrink-0">
              Ask
              <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </Button>
          </form>

          <div className="mt-7 flex flex-wrap gap-3 text-sm text-fci-steel dark:text-white/70">
            {["Daily crawler", "Temporary PDF chat", "10 Indian languages"].map((item) => (
              <span key={item} className="inline-flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-fci-primary" aria-hidden="true" />
                {item}
              </span>
            ))}
          </div>
        </motion.div>
      </div>
    </section>
  );
}
