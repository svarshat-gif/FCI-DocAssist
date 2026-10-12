"use client";

import { useInterface } from "@/contexts/interface-context";
import { FormEvent, KeyboardEvent, useState } from "react";
import { SendHorizontal } from "lucide-react";
import { PdfUploadButton } from "@/components/chat/pdf-upload-button";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import type { UploadSession } from "@/lib/types";

type ChatComposerProps = {
  disabled: boolean;
  busy: boolean;
  token?: string | null;
  onSend: (message: string) => void;
  onUploaded: (session: UploadSession) => void;
};

export function ChatComposer({
  disabled,
  busy,
  token,
  onSend,
  onUploaded,
}: ChatComposerProps) {
  const t = useInterface();
  const [value, setValue] = useState("");
  const [uploadBusy, setUploadBusy] = useState(false);

  function submit(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault();
    const message = value.trim();
    if (!message || disabled || uploadBusy) {
      return;
    }
    setValue("");
    onSend(message);
  }

  function keyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
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
        placeholder={t("Ask a question about FCI circulars")}
        aria-label="Message"
        className="min-h-16 border-0 bg-transparent focus:ring-0"
        disabled={disabled || uploadBusy}
      />
      <div className="flex items-center justify-between gap-2 px-2 pb-1">
        <div className="flex items-center gap-2">
          <PdfUploadButton token={token} onUploaded={onUploaded} disabled={busy} onBusyChange={setUploadBusy} />
        </div>
        <Button type="submit" size="icon" disabled={disabled || uploadBusy || !value.trim()} aria-label={t("Send")}>
          <SendHorizontal className="h-4 w-4" aria-hidden="true" />
        </Button>
      </div>
    </form>
  );
}
