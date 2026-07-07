"use client";

import { FormEvent, KeyboardEvent, useState } from "react";
import { SendHorizontal } from "lucide-react";
import { PdfUploadButton } from "@/components/chat/pdf-upload-button";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import type { UploadSession } from "@/lib/types";

type ChatComposerProps = {
  disabled: boolean;
  token?: string | null;
  onSend: (message: string) => void;
  onUploaded: (session: UploadSession) => void;
};

export function ChatComposer({
  disabled,
  token,
  onSend,
  onUploaded,
}: ChatComposerProps) {
  const [value, setValue] = useState("");

  function submit(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault();
    const message = value.trim();
    if (!message || disabled) {
      return;
    }
    setValue("");
    onSend(message);
  }

  function keyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  }

  return (
    <form
      onSubmit={submit}
      className="rounded-lg border border-fci-line bg-white p-2 shadow-soft dark:border-white/10 dark:bg-[#131b16]"
    >
      <Textarea
        value={value}
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={keyDown}
        placeholder="Ask a question about official FCI circulars"
        aria-label="Message"
        className="min-h-16 border-0 bg-transparent focus:ring-0"
        disabled={disabled}
      />
      <div className="flex items-center justify-between gap-2 px-2 pb-1">
        <div className="flex items-center gap-2">
          <PdfUploadButton token={token} onUploaded={onUploaded} />
          <span className="text-xs text-fci-steel dark:text-white/60">
            PDF mode is temporary
          </span>
        </div>
        <Button type="submit" disabled={disabled || !value.trim()} aria-label="Send message">
          <SendHorizontal className="h-4 w-4" aria-hidden="true" />
          Send
        </Button>
      </div>
    </form>
  );
}
