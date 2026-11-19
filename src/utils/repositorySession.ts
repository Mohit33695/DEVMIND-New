/**
 * Repository State & Backend Persistence Synchronization Utility.
 *
 * Purpose:
 * Synchronizes repository list and active repository selection with the backend API.
 * Ensures persistent repository state across browser refreshes and tab navigations,
 * maintaining backward compatibility with existing session event subscribers.
 */

import { fetchRepositories, deleteRepository } from '@/api/client';
import type { RepositorySummary } from '@/types/repository';

export const ACTIVE_REPO_KEY = 'devmind_active_repo_id';
export const REPOS_LIST_KEY = 'devmind_repositories';
export const REPO_CHANGED_EVENT = 'devmind_repo_changed';

export interface StoredRepositoryItem {
  repo_id: string;
  filename: string;
  size: number;
  uploaded_at: string;
  total_files: number;
  detected_languages: Record<string, number>;
  indexing_status?: string;
}

/**
 * Retrieves the cached list of repositories from browser storage.
 */
export function getStoredRepositories(): StoredRepositoryItem[] {
  try {
    const raw = localStorage.getItem(REPOS_LIST_KEY) || sessionStorage.getItem(REPOS_LIST_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

/**
 * Retrieves the current active repository ID from browser storage.
 */
export function getActiveRepositoryId(): string | null {
  try {
    return localStorage.getItem(ACTIVE_REPO_KEY) || sessionStorage.getItem(ACTIVE_REPO_KEY);
  } catch {
    return null;
  }
}

/**
 * Sets a specific repository as the active repository in both localStorage & sessionStorage,
 * and notifies listeners via custom DOM event.
 */
export function setActiveRepositoryId(repoId: string | null): void {
  try {
    if (repoId) {
      localStorage.setItem(ACTIVE_REPO_KEY, repoId);
      sessionStorage.setItem(ACTIVE_REPO_KEY, repoId);
    } else {
      localStorage.removeItem(ACTIVE_REPO_KEY);
      sessionStorage.removeItem(ACTIVE_REPO_KEY);
    }
  } catch {
    // Ignore browser storage write errors
  }

  window.dispatchEvent(
    new CustomEvent(REPO_CHANGED_EVENT, { detail: { repoId } })
  );
}

/**
 * Caches repositories list in both storage mechanisms.
 */
function cacheRepositories(repos: StoredRepositoryItem[]): void {
  try {
    const serialized = JSON.stringify(repos);
    localStorage.setItem(REPOS_LIST_KEY, serialized);
    sessionStorage.setItem(REPOS_LIST_KEY, serialized);
  } catch {
    // Ignore storage quota errors
  }
}

/**
 * Synchronizes repository list from the backend API.
 * Updates local cache and validates / restores active repository selection.
 */
export async function syncRepositoriesWithBackend(): Promise<StoredRepositoryItem[]> {
  try {
    const backendRepos: RepositorySummary[] = await fetchRepositories();
    const mapped: StoredRepositoryItem[] = backendRepos.map((r) => ({
      repo_id: r.repo_id,
      filename: r.filename,
      size: r.size,
      uploaded_at: r.uploaded_at,
      total_files: r.total_files,
      detected_languages: r.detected_languages || {},
      indexing_status: r.indexing_status || 'not_indexed',
    }));

    cacheRepositories(mapped);

    const currentActive = getActiveRepositoryId();
    if (mapped.length > 0) {
      const activeStillExists = currentActive && mapped.some((r) => r.repo_id === currentActive);
      if (!activeStillExists) {
        // Auto-select the first repository if current is missing or invalid
        setActiveRepositoryId(mapped[0].repo_id);
      } else {
        // Re-affirm current active selection
        setActiveRepositoryId(currentActive);
      }
    } else {
      setActiveRepositoryId(null);
    }

    return mapped;
  } catch {
    // Fallback to locally cached repositories on network failure
    return getStoredRepositories();
  }
}

/**
 * Adds or updates a repository entry locally and sets it active.
 */
export function saveStoredRepository(item: StoredRepositoryItem): void {
  const currentList = getStoredRepositories();
  const existingIdx = currentList.findIndex((r) => r.repo_id === item.repo_id);

  let updatedList: StoredRepositoryItem[];
  if (existingIdx >= 0) {
    updatedList = [...currentList];
    updatedList[existingIdx] = { ...updatedList[existingIdx], ...item };
  } else {
    updatedList = [item, ...currentList];
  }

  cacheRepositories(updatedList);
  setActiveRepositoryId(item.repo_id);
}

/**
 * Deletes a repository both on the backend and in local storage,
 * updating active repository selection safely.
 */
export async function deleteStoredRepository(repoId: string): Promise<void> {
  // 1. Delete on backend
  await deleteRepository(repoId);

  // 2. Remove from local cache
  const currentList = getStoredRepositories();
  const filtered = currentList.filter((r) => r.repo_id !== repoId);
  cacheRepositories(filtered);

  // 3. Update active repository selection
  const currentActive = getActiveRepositoryId();
  if (currentActive === repoId) {
    const nextActive = filtered.length > 0 ? filtered[0].repo_id : null;
    setActiveRepositoryId(nextActive);
  } else {
    setActiveRepositoryId(currentActive);
  }
}

/**
 * Backward compatibility alias for local removal.
 */
export function removeStoredRepository(repoId: string): void {
  deleteStoredRepository(repoId).catch(() => {
    // Fallback local removal
    const currentList = getStoredRepositories();
    const filtered = currentList.filter((r) => r.repo_id !== repoId);
    cacheRepositories(filtered);
    const currentActive = getActiveRepositoryId();
    if (currentActive === repoId) {
      setActiveRepositoryId(filtered.length > 0 ? filtered[0].repo_id : null);
    }
  });
}
