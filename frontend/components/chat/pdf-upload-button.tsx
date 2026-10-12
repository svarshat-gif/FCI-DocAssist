"use client";

import { useInterface } from "@/contexts/interface-context";
import { ChangeEvent, useRef, useState } from "react";
import { FileUp, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import type { UploadSession } from "@/lib/types";
import * as Dialog from "@radix-ui/react-dialog";

type PdfUploadButtonProps = {
  token?: string | null;
  onUploaded: (session: UploadSession) => void;
  disabled?: boolean;
  onBusyChange?: (busy: boolean) => void;
};

export function PdfUploadButton({ token, onUploaded, disabled, onBusyChange }: PdfUploadButtonProps) {
  const t = useInterface();
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const [policy, setPolicy] = useState<Awaited<ReturnType<typeof api.uploadPolicy>> | null>(null);
  const [policyLoading, setPolicyLoading] = useState(false);
  const [consent, setConsent] = useState(false);
  const [open, setOpen] = useState(false);

  async function selectFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }
    event.target.value = "";
    setPendingFile(file);
    setConsent(false);
    setPolicy(null);
    setOpen(true);
    setPolicyLoading(true);
    setError(null);
    try {
      const settings = await api.uploadPolicy();
      if (file.size > settings.max_upload_mb * 1024 * 1024) throw new Error(`PDF upload limit is ${settings.max_upload_mb} MB.`);
      setPolicy(settings);
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Upload settings could not be loaded."); }
    finally { setPolicyLoading(false); }
  }

  async function upload() {
    if (!pendingFile || !policy || (policy.google_processing && !consent)) return;
    setLoading(true);
    onBusyChange?.(true);
    setError(null);
    try {
      const session = await api.uploadPdf(pendingFile, token, consent);
      onUploaded(session);
      setOpen(false);
      setPendingFile(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "PDF upload failed.");
    } finally {
      setLoading(false);
      onBusyChange?.(false);
    }
  }

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf"
        className="hidden"
        onChange={selectFile}
      />
      <Button
        type="button"
        variant="secondary"
        size="icon"
        title={t("Upload PDF")}
        aria-label={t("Upload PDF")}
        onClick={() => inputRef.current?.click()}
        disabled={disabled || loading || policyLoading || !token}
      >
        {loading ? (
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
        ) : (
          <FileUp className="h-4 w-4" aria-hidden="true" />
        )}
      </Button>
      <Dialog.Root open={open} onOpenChange={(value) => { if (!loading) setOpen(value); }}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 z-50 bg-black/40" />
          <Dialog.Content className="fixed left-1/2 top-1/2 z-50 max-h-[85dvh] w-[calc(100vw-2rem)] max-w-md -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-lg border border-fci-line bg-white p-6 shadow-soft dark:border-white/10 dark:bg-[#101712] dark:text-white">
            <Dialog.Title className="text-lg font-semibold">Upload PDF</Dialog.Title>
            <Dialog.Description className="mt-3 break-all text-sm text-fci-steel dark:text-white/70">{pendingFile?.name}</Dialog.Description>
            {policyLoading ? <p role="status" className="mt-4 text-sm">Checking upload settings...</p> : null}
            {policy ? <>
              <p className="mt-4 text-sm text-fci-steel dark:text-white/70">PDF access expires after {policy.expires_minutes} minutes. Saved chats remain until you delete them.</p>
              {policy.google_processing ? <label className="mt-4 flex items-start gap-3 text-sm leading-6">
                <input type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} disabled={loading} className="mt-1.5 h-4 w-4 shrink-0 accent-fci-primary" />
                <span>I agree to send this document&apos;s text to Google for document search and answers. Google&apos;s free-tier terms may allow this content to improve its products. Do not upload confidential documents.</span>
              </label> : null}
            </> : null}
            {error ? <p role="alert" className="mt-4 text-sm text-red-700 dark:text-red-300">{error}</p> : null}
            <div className="mt-6 flex justify-end gap-2">
              <Button type="button" variant="ghost" disabled={loading} onClick={() => setOpen(false)}>Cancel</Button>
              <Button type="button" disabled={loading || !policy || (policy.google_processing && !consent)} onClick={upload}>
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileUp className="h-4 w-4" />}Upload PDF
              </Button>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </>
  );
}
