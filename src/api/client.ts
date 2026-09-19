import type {
  RepositoryUploadResponse,
  RepositoryScanResult,
  RepositoryFileContentResponse,
  RepositorySymbolsResponse,
  SymbolItem,
  FileSymbols,
  SearchResultItem,
  RepositorySearchResponse,
  SearchOptions,
} from '@/types/repository';

export type {
  RepositoryUploadResponse,
  RepositoryScanResult,
  RepositoryFileContentResponse,
  RepositorySymbolsResponse,
  SymbolItem,
  FileSymbols,
  SearchResultItem,
  RepositorySearchResponse,
  SearchOptions,
};

export interface HealthResponse {
  status: string;
  service: string;
}


const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

/**
 * Reusable HTTP API client for DevMind backend requests.
 */

// 1. Health check GET request
export async function fetchHealthCheck(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE_URL}/api/health`, {
    method: 'GET',
    headers: {
      'Accept': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Health check request failed with HTTP ${response.status}`);
  }

  return response.json();
}

// 2. Repository ZIP upload POST request
export async function uploadRepositoryZip(file: File): Promise<RepositoryUploadResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE_URL}/api/repositories/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    let errorDetail = `Upload failed with HTTP status ${response.status}`;
    try {
      const errorJson = await response.json();
      if (errorJson && errorJson.detail) {
        errorDetail = typeof errorJson.detail === 'string' ? errorJson.detail : JSON.stringify(errorJson.detail);
      }
    } catch {
      // Fallback if response body isn't JSON
    }
    throw new Error(errorDetail);
  }

  return response.json();
}

// 3. Repository File Content GET request
export async function fetchFileContent(
  repoId: string,
  filePath: string
): Promise<RepositoryFileContentResponse> {
  const encodedPath = encodeURIComponent(filePath);
  const response = await fetch(
    `${API_BASE_URL}/api/repositories/${repoId}/files/content?path=${encodedPath}`,
    {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
    }
  );

  if (!response.ok) {
    let errorDetail = `Failed to load file content (HTTP ${response.status})`;
    try {
      const errorJson = await response.json();
      if (errorJson && errorJson.detail) {
        errorDetail = typeof errorJson.detail === 'string' ? errorJson.detail : JSON.stringify(errorJson.detail);
      }
    } catch {
      // Fallback if response isn't JSON
    }
    throw new Error(errorDetail);
  }

  return response.json();
}

// 4. Repository Code Symbols GET request
export async function fetchRepositorySymbols(
  repoId: string
): Promise<RepositorySymbolsResponse> {
  const response = await fetch(`${API_BASE_URL}/api/repositories/${repoId}/symbols`, {
    method: 'GET',
    headers: {
      'Accept': 'application/json',
    },
  });

  if (!response.ok) {
    let errorDetail = `Failed to load repository symbols (HTTP ${response.status})`;
    try {
      const errorJson = await response.json();
      if (errorJson && errorJson.detail) {
        errorDetail = typeof errorJson.detail === 'string' ? errorJson.detail : JSON.stringify(errorJson.detail);
      }
    } catch {
      // Fallback if response isn't JSON
    }
    throw new Error(errorDetail);
  }

  return response.json();
}

// 5. Repository Code Search GET request
export async function searchRepositoryCode(
  repoId: string,
  query: string,
  options: SearchOptions = {}
): Promise<RepositorySearchResponse> {
  const params = new URLSearchParams();
  params.append('q', query);
  if (options.case_sensitive) {
    params.append('case_sensitive', 'true');
  }
  if (options.max_results !== undefined) {
    params.append('max_results', options.max_results.toString());
  }
  if (options.file_extension) {
    params.append('file_extension', options.file_extension);
  }

  const response = await fetch(
    `${API_BASE_URL}/api/repositories/${repoId}/search?${params.toString()}`,
    {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
    }
  );

  if (!response.ok) {
    let errorDetail = `Code search failed (HTTP ${response.status})`;
    try {
      const errorJson = await response.json();
      if (errorJson && errorJson.detail) {
        errorDetail = typeof errorJson.detail === 'string' ? errorJson.detail : JSON.stringify(errorJson.detail);
      }
    } catch {
      // Fallback if response body isn't JSON
    }
    throw new Error(errorDetail);
  }

  return response.json();
}



