import "@testing-library/jest-dom/vitest";
import { vi } from "vitest";

// jsdom lacks these browser APIs that motion and our components touch
class IO {
  observe() {}
  unobserve() {}
  disconnect() {}
  takeRecords() { return []; }
}
Object.defineProperty(window, "IntersectionObserver", { writable: true, value: IO });
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: query.includes("prefers-reduced-motion") ? true : false,
    media: query, onchange: null, addListener: vi.fn(), removeListener: vi.fn(),
    addEventListener: vi.fn(), removeEventListener: vi.fn(), dispatchEvent: vi.fn(),
  })),
});
vi.mock("next/cache", () => ({ cacheLife: () => {} }));
