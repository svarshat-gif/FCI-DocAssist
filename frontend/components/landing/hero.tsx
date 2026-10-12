"use client";

import localFont from "next/font/local";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { motion } from "framer-motion";
import { ArrowRight, CheckCircle2, FileSearch, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";

const handwriting = localFont({
  src: "../../public/fonts/caveat-variable.ttf",
  display: "swap",
  weight: "400 700",
  fallback: ["Segoe Print", "Bradley Hand", "cursive"],
});

export function Hero() {
  const router = useRouter();
  const [prompt, setPrompt] = useState("");

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const query = prompt.trim();
    router.push(query ? `/chat?prompt=${encodeURIComponent(query)}` : "/chat");
  }

  return (
    <section className="hero-paper relative flex min-h-[78svh] items-center overflow-hidden">

      <div className="relative mx-auto flex w-full max-w-7xl flex-col px-5 py-12 sm:px-8 sm:py-16 lg:px-10 lg:py-20">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.65, ease: "easeOut" }}
          className="max-w-3xl"
        >
          <div className="mb-5 inline-flex items-center gap-2 text-sm font-medium text-fci-dark">
            <ShieldCheck className="h-4 w-4" aria-hidden="true" />
            Answers linked to official FCI circulars
          </div>
          <h1 className={`${handwriting.className} text-[3.25rem] font-medium leading-[1.12] text-fci-dark sm:text-7xl lg:text-[5.5rem]`}>
            <span className="block">FCI Doc Assist</span>
          </h1>
          <p className="mt-6 max-w-2xl text-lg leading-8 text-fci-steel">
            Find the circular you need. Ask a question, get a clear summary,
            and pick up your conversation whenever you return.
          </p>

          <form
            onSubmit={submit}
            className="mt-9 flex max-w-2xl items-center gap-2 rounded-lg border border-fci-dark/15 bg-white/80 p-2 shadow-crisp"
          >
            <FileSearch className="ml-3 h-5 w-5 shrink-0 text-fci-primary" aria-hidden="true" />
            <input
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
              className="h-12 min-w-0 flex-1 bg-transparent text-base text-fci-ink outline-none placeholder:text-fci-steel/60"
              placeholder="Summarize Circular 18/2024"
              aria-label="Ask about FCI circulars"
            />
            <Button type="submit" className="shrink-0">
              Ask
              <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </Button>
          </form>

          <div className="mt-7 flex flex-wrap gap-3 text-sm text-fci-steel">
            {["Daily circular updates", "Your PDFs", "10 Indian languages"].map((item) => (
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
