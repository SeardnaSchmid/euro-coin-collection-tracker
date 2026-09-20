export const STORAGE_KEY = "euro-coins.collection.v1";

export type StoredCollection = {
  version: 1;
  updatedAt: string;
  collectedIds: string[];
};

export function normalizeCollection(
  value: unknown,
  knownIds: ReadonlySet<string>,
): StoredCollection {
  const source = value && typeof value === "object" ? value as Partial<StoredCollection> : {};
  const collectedIds = Array.isArray(source.collectedIds)
    ? [...new Set(source.collectedIds.filter((id): id is string => typeof id === "string" && knownIds.has(id)))]
    : [];

  return {
    version: 1,
    updatedAt: typeof source.updatedAt === "string" ? source.updatedAt : new Date(0).toISOString(),
    collectedIds,
  };
}

export function loadCollection(knownIds: ReadonlySet<string>): StoredCollection {
  try {
    return normalizeCollection(JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "null"), knownIds);
  } catch {
    return normalizeCollection(null, knownIds);
  }
}

export function saveCollection(collectedIds: Iterable<string>): StoredCollection {
  const collection: StoredCollection = {
    version: 1,
    updatedAt: new Date().toISOString(),
    collectedIds: [...collectedIds].sort(),
  };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(collection));
  return collection;
}

export function clearCollection(): void {
  localStorage.removeItem(STORAGE_KEY);
}
