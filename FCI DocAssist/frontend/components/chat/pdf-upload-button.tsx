"use client";

import { ChangeEvent, useRef, useState } from "react";
import { FileUp, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import type { UploadSession } from "@/lib/types";

type PdfUploadButtonProps = {
  token?: string | null;
  onUploaded: (session: UploadSession) => void;
};

export function PdfUploadButton({ token, onUploaded }: PdfUploadButtonProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [loading, setLoading] = useState(false);

  async function upload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }
    setLoading(true);
    try {
      const session = await api.uploadPdf(file, token);
      onUploaded(session);
    } finally {
      setLoading(false);
      event.target.value = "";
    }
  }

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf"
        className="hidden"
        onChange={upload}
      />
      <Button
        type="button"
        variant="secondary"
        size="icon"
        title="Upload PDF"
        aria-label="Upload PDF"
        onClick={() => inputRef.current?.click()}
        disabled={loading}
      >
        {loading ? (
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
        ) : (
          <FileUp className="h-4 w-4" aria-hidden="true" />
        )}
      </Button>
    </>
  );
}
