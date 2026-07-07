export type Citation = {
  source_id: string;
  circular_number?: string | null;
  title: string;
  publication_date?: string | null;
  official_url: string;
  page_number?: number | null;
  snippet: string;
};

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  created_at?: string;
};

export type ChatResponse = {
  conversation_id: string;
  answer: string;
  citations: Citation[];
  found: boolean;
};

export type Conversation = {
  id: string;
  title: string;
  language: string;
  source_mode: "official" | "upload";
  upload_session_id?: string | null;
  created_at: string;
  updated_at: string;
};

export type Circular = {
  id: string;
  circular_number?: string | null;
  title: string;
  publication_date?: string | null;
  department?: string | null;
  topic?: string | null;
  official_url: string;
  page_count: number;
};

export type UploadSession = {
  id: string;
  filename: string;
  page_count: number;
  expires_at: string;
};

export type User = {
  id: string;
  email: string;
  full_name?: string | null;
  is_active: boolean;
};
