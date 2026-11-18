// Mirrors apps/api/app/schemas.py — the API contract.
export type Institution = {
  name: string;
  founded?: number | null;
  city?: string | null;
  country?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  homepage?: string | null;
  description?: string | null;
  images: { url: string; author: string; license: string; source: string; alt: string }[];
};

export type Overview = {
  works: number;
  citations: number;
  oa_share: number;
  faculty: number;
  faculty_linked: number;
  partner_institutions: number;
  outliers: number;
  duplicates: number;
  computed_at: string | null;
  institution: Institution | null;
};

export type StatsKey = "monthly" | "types" | "fields" | "rising_topics" | "top_venues" | "top_partners" | "top_faculty";

export type StatsData = {
  monthly: { month: string; count: number }[];
  types: { type: string; count: number }[];
  fields: { field: string; count: number; subfields: { name: string; count: number }[] }[];
  rising_topics: { id: string; name: string; field: string; recent: number; prior: number; growth: number }[];
  top_venues: { name: string; count: number }[];
  top_partners: { id: string; name: string; country: string | null; count: number }[];
  top_faculty: { id: number; name: string; count: number }[];
};

export type AuthorRef = { name: string; faculty_id: number | null };

export type WorkCard = {
  id: string;
  title: string;
  publication_date: string | null;
  type: string | null;
  venue: string | null;
  cited_by_count: number;
  is_oa: boolean;
  doi: string | null;
  field: string | null;
  uiuc_authors: AuthorRef[];
};

export type Page<T> = { items: T[]; total: number; page: number; page_size: number };

export type FacultyCard = {
  id: number;
  name: string;
  position: string | null;
  photo_url: string | null;
  primary_field: string | null;
  keywords: string[];
  matched_keywords: string[];
  link_confidence: number | null;
};

export type FacultyProfile = FacultyCard & {
  link_method: string | null;
  openalex_author_ids: string[];
  recent_works: WorkCard[];
  topics: { name: string; count: number }[];
};
