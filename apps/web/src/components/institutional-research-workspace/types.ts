/** Presentation types for RC1 M8 Institutional Research Workspace. */

export type WorkspaceNote = {
  note_id: string;
  title?: string;
  body?: string;
  format?: string;
  folder_id?: string;
  status?: string;
  company?: string | null;
  portfolio_id?: string | null;
  research_object_id?: string | null;
  version?: number;
  updated_at?: string;
  tag_ids?: string[];
  assignee_id?: string | null;
  ai_generated?: boolean;
  workflow_id?: string | null;
};

export type WorkspaceFolder = {
  folder_id: string;
  name?: string;
  parent_id?: string | null;
  archived?: boolean;
};

export type WorkspaceBookmark = {
  bookmark_id: string;
  kind?: string;
  label?: string;
  target_id?: string | null;
  company?: string | null;
  href?: string | null;
};

export type WorkspaceComment = {
  comment_id: string;
  note_id?: string;
  body?: string;
  author_id?: string | null;
  resolved?: boolean;
  created_at?: string;
};

export type WorkspaceVersion = {
  version: number;
  saved_at?: string;
  title?: string;
  body?: string;
};

export type WorkspaceDashboard = {
  recent_notes?: WorkspaceNote[];
  pending_reviews?: WorkspaceNote[];
  published_reports?: WorkspaceNote[];
  bookmarks?: WorkspaceBookmark[];
  recent_copilot_conversations?: Array<Record<string, unknown>>;
  recent_companies?: string[];
  tasks?: Array<Record<string, unknown>>;
  open_comments?: WorkspaceComment[];
  folders?: WorkspaceFolder[];
  tags?: Array<Record<string, unknown>>;
};
