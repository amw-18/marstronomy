import "./styles.css";

import { DEFAULT_SITE } from "./constants";
import { createMarsObserverApp } from "./app";
import { loadRuntimeCatalog } from "./catalog";
import { readStateFromSearch } from "./urlState";

async function bootstrap(): Promise<void> {
  const root = document.querySelector<HTMLElement>("#app");
  if (!root) {
    throw new Error("Missing #app root element.");
  }

  root.innerHTML = `
    <div class="loading-state">
      <p class="eyebrow">Mars Observer</p>
      <h1>Loading sky vectors…</h1>
      <p>Preparing stars, the Sun, and both moons for ${DEFAULT_SITE.name}.</p>
    </div>
  `;

  try {
    const stars = await loadRuntimeCatalog();
    createMarsObserverApp(root, {
      stars,
      initialState: readStateFromSearch(window.location.search),
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    root.innerHTML = `
      <div class="loading-state loading-state--error">
        <p class="eyebrow">Mars Observer</p>
        <h1>Viewer failed to load</h1>
        <p>${message}</p>
      </div>
    `;
  }
}

void bootstrap();
