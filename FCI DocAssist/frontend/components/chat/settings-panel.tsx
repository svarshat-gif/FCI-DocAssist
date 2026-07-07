"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { Download, Settings, Trash2, X } from "lucide-react";
import { LanguageSelector } from "@/components/chat/language-selector";
import { Button } from "@/components/ui/button";
import { useTheme } from "@/contexts/theme-context";
import type { SupportedLanguage } from "@/lib/languages";

type SettingsPanelProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  language: SupportedLanguage;
  onLanguageChange: (language: SupportedLanguage) => void;
  fontScale: number;
  onFontScaleChange: (value: number) => void;
  canExport: boolean;
  onExport: (format: "pdf" | "txt") => void;
  onClearHistory: () => void;
};

export function SettingsPanel({
  open,
  onOpenChange,
  language,
  onLanguageChange,
  fontScale,
  onFontScaleChange,
  canExport,
  onExport,
  onClearHistory,
}: SettingsPanelProps) {
  const { theme, toggleTheme } = useTheme();

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-black/35 backdrop-blur-sm" />
        <Dialog.Content className="fixed right-4 top-4 z-50 w-[calc(100vw-2rem)] max-w-md rounded-lg border border-fci-line bg-white p-5 shadow-soft outline-none dark:border-white/10 dark:bg-[#101712]">
          <div className="flex items-center justify-between">
            <Dialog.Title className="flex items-center gap-2 text-lg font-semibold text-fci-ink dark:text-white">
              <Settings className="h-5 w-5 text-fci-primary" aria-hidden="true" />
              Settings
            </Dialog.Title>
            <Dialog.Close asChild>
              <Button variant="ghost" size="icon" aria-label="Close settings">
                <X className="h-4 w-4" aria-hidden="true" />
              </Button>
            </Dialog.Close>
          </div>

          <div className="mt-6 space-y-6">
            <section>
              <h3 className="text-sm font-semibold text-fci-ink dark:text-white">Theme</h3>
              <button
                type="button"
                onClick={toggleTheme}
                className="mt-3 flex w-full items-center justify-between rounded-lg border border-fci-line bg-fci-mist px-4 py-3 text-sm font-medium text-fci-ink transition hover:border-fci-primary/30 dark:border-white/10 dark:bg-white/10 dark:text-white"
              >
                <span>{theme === "dark" ? "Dark" : "Light"}</span>
                <span className="h-5 w-10 rounded-full bg-fci-primary/20 p-0.5">
                  <span
                    className={`block h-4 w-4 rounded-full bg-fci-primary transition ${
                      theme === "dark" ? "translate-x-5" : "translate-x-0"
                    }`}
                  />
                </span>
              </button>
            </section>

            <section>
              <h3 className="mb-3 text-sm font-semibold text-fci-ink dark:text-white">
                Language
              </h3>
              <LanguageSelector value={language} onChange={onLanguageChange} />
            </section>

            <section>
              <h3 className="text-sm font-semibold text-fci-ink dark:text-white">Font size</h3>
              <input
                aria-label="Font size"
                className="mt-4 w-full accent-fci-primary"
                type="range"
                min="0.9"
                max="1.2"
                step="0.05"
                value={fontScale}
                onChange={(event) => onFontScaleChange(Number(event.target.value))}
              />
            </section>

            <section>
              <h3 className="mb-3 text-sm font-semibold text-fci-ink dark:text-white">
                Chat export
              </h3>
              <div className="grid grid-cols-2 gap-2">
                <Button
                  type="button"
                  variant="secondary"
                  disabled={!canExport}
                  onClick={() => onExport("pdf")}
                >
                  <Download className="h-4 w-4" aria-hidden="true" />
                  PDF
                </Button>
                <Button
                  type="button"
                  variant="secondary"
                  disabled={!canExport}
                  onClick={() => onExport("txt")}
                >
                  <Download className="h-4 w-4" aria-hidden="true" />
                  TXT
                </Button>
              </div>
            </section>

            <Button type="button" variant="danger" className="w-full" onClick={onClearHistory}>
              <Trash2 className="h-4 w-4" aria-hidden="true" />
              Clear history
            </Button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
