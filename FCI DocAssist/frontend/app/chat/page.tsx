import { Suspense } from "react";
import { ChatShell } from "@/components/chat/chat-shell";

export default function ChatPage() {
  return (
    <Suspense fallback={<div className="p-6">Loading chat...</div>}>
      <ChatShell />
    </Suspense>
  );
}
