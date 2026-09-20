/**
 * Repository Session Storage & State Management Utility.
 *
 * Purpose:
 * Provides central helper functions to read, store, update, and manage
 * active repository selection and uploaded repository lists in sessionStorage,
 * broadcasting changes via browser custom events.
 */

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
}

/**
 * Retrieves the list of stored uploaded repositories from sessionStorage.
 */
export function getStoredRepositories(): StoredRepositoryItem[] {
  try {
    const raw = sessionStorage.getItem(REPOS_LIST_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

/**
 * Retrieves the current active repository ID from sessionStorage.
 */
export function getActiveRepositoryId(): string | null {
  return sessionStorage.getItem(ACTIVE_REPO_KEY);
}

/**
 * Sets a specific repository as the active repository and notifies listeners.
 */
export function setActiveRepositoryId(repoId: string): void {
  sessionStorage.setItem(ACTIVE_REPO_KEY, repoId);
  window.dispatchEvent(new CustomEvent(REPO_CHANGED_EVENT, { detail: { repoId } }));
}

/**
 * Adds or updates a repository entry in sessionStorage and selects it as active.
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

  sessionStorage.setItem(REPOS_LIST_KEY, JSON.stringify(updatedList));
  setActiveRepositoryId(item.repo_id);
}

/**
 * Removes a repository entry from sessionStorage.
 */
export function removeStoredRepository(repoId: string): void {
  const currentList = getStoredRepositories();
  const filtered = currentList.filter((r) => r.repo_id !== repoId);
  sessionStorage.setItem(REPOS_LIST_KEY, JSON.stringify(filtered));

  const activeId = getActiveRepositoryId();
  if (activeId === repoId) {
    const nextActive = filtered.length > 0 ? filtered[0].repo_id : '';
    if (nextActive) {
      setActiveRepositoryId(nextActive);
    } else {
      sessionStorage.removeItem(ACTIVE_REPO_KEY);
      window.dispatchEvent(new CustomEvent(REPO_CHANGED_EVENT, { detail: { repoId: null } }));
    }
  } else {
    window.dispatchEvent(new CustomEvent(REPO_CHANGED_EVENT, { detail: { repoId: activeId } }));
  }
}
