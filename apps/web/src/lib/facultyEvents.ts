"use client";

/** Any component can open the faculty drawer (e.g. an author name in a publication card). */
export const FACULTY_EVENT = "portal:open-faculty";
export function openFaculty(id: number) {
  window.dispatchEvent(new CustomEvent<number>(FACULTY_EVENT, { detail: id }));
}
