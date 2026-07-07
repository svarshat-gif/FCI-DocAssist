"use client";

import { motion } from "framer-motion";

const stats = [
  { label: "Official source mode", value: "FCI" },
  { label: "Supported languages", value: "10" },
  { label: "Citation policy", value: "Strict" },
  { label: "Upload storage", value: "Temporary" },
];

export function StatStrip() {
  return (
    <section className="border-y border-fci-line bg-fci-light/60 px-5 py-8 dark:border-white/10 dark:bg-fci-primary/10 sm:px-8 lg:px-10">
      <div className="mx-auto grid max-w-7xl gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat, index) => (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, y: 12 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: index * 0.05 }}
            className="rounded-lg border border-white/80 bg-white/70 p-5 shadow-sm backdrop-blur dark:border-white/10 dark:bg-white/10"
          >
            <div className="text-3xl font-semibold text-fci-dark dark:text-fci-light">
              {stat.value}
            </div>
            <div className="mt-1 text-sm font-medium text-fci-steel dark:text-white/70">
              {stat.label}
            </div>
          </motion.div>
        ))}
      </div>
    </section>
  );
}
