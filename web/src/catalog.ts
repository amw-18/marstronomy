import type { RuntimeStar } from "./types";

export async function loadRuntimeCatalog(url = "/data/stars.min.json"): Promise<RuntimeStar[]> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to load star catalog: ${response.status} ${response.statusText}`);
  }
  return (await response.json()) as RuntimeStar[];
}
