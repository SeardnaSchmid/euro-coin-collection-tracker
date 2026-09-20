import assert from "node:assert/strict";
import test from "node:test";
import { clearCollection, loadCollection, normalizeCollection, saveCollection, STORAGE_KEY } from "./storage.ts";

const knownIds = new Set(["de-first-series-200", "fr-first-series-100"]);
const memory = new Map<string, string>();

Object.defineProperty(globalThis, "localStorage", {
  configurable: true,
  value: {
    getItem: (key: string) => memory.get(key) ?? null,
    setItem: (key: string, value: string) => memory.set(key, value),
    removeItem: (key: string) => memory.delete(key),
  },
});

void test("normalizes a saved collection and removes duplicates", () => {
  assert.deepEqual(
    normalizeCollection({
      version: 1,
      updatedAt: "2026-09-20T12:00:00.000Z",
      collectedIds: ["de-first-series-200", "de-first-series-200", "fr-first-series-100"],
    }, knownIds),
    {
      version: 1,
      updatedAt: "2026-09-20T12:00:00.000Z",
      collectedIds: ["de-first-series-200", "fr-first-series-100"],
    },
  );
});

void test("ignores unknown catalogue ids during import", () => {
  assert.deepEqual(
    normalizeCollection({ collectedIds: ["removed-coin", "fr-first-series-100"] }, knownIds).collectedIds,
    ["fr-first-series-100"],
  );
});

void test("recovers from invalid imported shapes", () => {
  assert.deepEqual(normalizeCollection("not a collection", knownIds).collectedIds, []);
  assert.deepEqual(normalizeCollection({ collectedIds: "not an array" }, knownIds).collectedIds, []);
});

void test("saves, loads, and clears a browser-local collection", () => {
  memory.clear();
  const saved = saveCollection(["fr-first-series-100", "de-first-series-200"]);

  assert.deepEqual(saved.collectedIds, ["de-first-series-200", "fr-first-series-100"]);
  assert.deepEqual(loadCollection(knownIds).collectedIds, saved.collectedIds);
  assert.ok(memory.has(STORAGE_KEY));

  clearCollection();
  assert.equal(memory.has(STORAGE_KEY), false);
  assert.deepEqual(loadCollection(knownIds).collectedIds, []);
});
