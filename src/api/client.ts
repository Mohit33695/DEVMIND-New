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
  DependencyItem,
  RepositoryDependenciesResponse,
  DependencyType,
  ResolutionStatus,
  RepositoryDocumentationResponse,
  ModuleDocItem,
  OverviewDocSummary,
  ArchitectureDocSummary,
  RepositoryQualityResponse,
  QualityFindingItem,
  QualityMetricsSummary,
  FileQualitySummary,
  RepositorySecurityResponse,
  SecurityFindingItem,
  SecurityMetricsSummary,
  RepositoryTestingResponse,
  TestFileSummary,
  SourceTestMapping,
  TestingFindingItem,
  TestingMetricsSummary,
  RepositoryGitResponse,
  GitCommitItem,
  GitContributorItem,
  GitFileHistoryItem,
  GitActivityPoint,
  GitRepositorySummary,
  RepositoryIndexStatus,
  RepositoryRetrievalResponse,
  RetrievalResult,
  SourceReference,
  CodeChunk,
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
  DependencyItem,
  RepositoryDependenciesResponse,
  DependencyType,
  ResolutionStatus,
  RepositoryDocumentationResponse,
  ModuleDocItem,
  OverviewDocSummary,
  ArchitectureDocSummary,
  RepositoryQualityResponse,
  QualityFindingItem,
  QualityMetricsSummary,
  FileQualitySummary,
  RepositorySecurityResponse,
  SecurityFindingItem,
  SecurityMetricsSummary,
  RepositoryTestingResponse,
  TestFileSummary,
  SourceTestMapping,
  TestingFindingItem,
  TestingMetricsSummary,
  RepositoryGitResponse,
  GitCommitItem,
  GitContributorItem,
  GitFileHistoryItem,
  GitActivityPoint,
  GitRepositorySummary,
  RepositoryIndexStatus,
  RepositoryRetrievalResponse,
  RetrievalResult,
  SourceReference,
  CodeChunk,
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

// 6. Repository Dependencies GET request
export async function fetchRepositoryDependencies(
  repoId: string
): Promise<RepositoryDependenciesResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/repositories/${repoId}/dependencies`,
    {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
    }
  );

  if (!response.ok) {
    let errorDetail = `Failed to load repository dependencies (HTTP ${response.status})`;
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

// 7. Repository Documentation GET request
export async function fetchRepositoryDocumentation(
  repoId: string
): Promise<RepositoryDocumentationResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/repositories/${repoId}/documentation`,
    {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
    }
  );

  if (!response.ok) {
    let errorDetail = `Failed to load repository documentation (HTTP ${response.status})`;
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

// 8. Repository Quality GET request
export async function fetchRepositoryQuality(
  repoId: string
): Promise<RepositoryQualityResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/repositories/${repoId}/quality`,
    {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
    }
  );

  if (!response.ok) {
    let errorDetail = `Failed to load repository quality analysis (HTTP ${response.status})`;
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

// 9. Repository Security GET request
export async function fetchRepositorySecurity(
  repoId: string
): Promise<RepositorySecurityResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/repositories/${repoId}/security`,
    {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
    }
  );

  if (!response.ok) {
    let errorDetail = `Failed to load repository security analysis (HTTP ${response.status})`;
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

// 10. Repository Testing Intelligence GET request
export async function fetchRepositoryTesting(repoId: string): Promise<RepositoryTestingResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/repositories/${encodeURIComponent(repoId)}/testing`,
    {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
    }
  );

  if (!response.ok) {
    let errorDetail = `Failed to load repository testing analysis (HTTP ${response.status})`;
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

// 11. Repository Git Intelligence GET request
export async function fetchRepositoryGit(
  repoId: string,
  maxCommits: number = 200
): Promise<RepositoryGitResponse> {
  const params = new URLSearchParams({
    max_commits: maxCommits.toString(),
  });

  const response = await fetch(
    `${API_BASE_URL}/api/repositories/${encodeURIComponent(repoId)}/git?${params.toString()}`,
    {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
    }
  );

  if (!response.ok) {
    let errorDetail = `Failed to load repository Git metadata (HTTP ${response.status})`;
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

// 12. RAG Index Status GET request
export async function fetchRepositoryIndexStatus(repoId: string): Promise<RepositoryIndexStatus> {
  const response = await fetch(
    `${API_BASE_URL}/api/repositories/${encodeURIComponent(repoId)}/index/status`,
    {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
    }
  );

  if (!response.ok) {
    let errorDetail = `Failed to get index status (HTTP ${response.status})`;
    try {
      const errorJson = await response.json();
      if (errorJson && errorJson.detail) {
        errorDetail = typeof errorJson.detail === 'string' ? errorJson.detail : JSON.stringify(errorJson.detail);
      }
    } catch {
      // Fallback
    }
    throw new Error(errorDetail);
  }

  return response.json();
}

// 13. RAG Index Repository POST request
export async function indexRepositoryRAG(repoId: string): Promise<RepositoryIndexStatus> {
  const response = await fetch(
    `${API_BASE_URL}/api/repositories/${encodeURIComponent(repoId)}/index`,
    {
      method: 'POST',
      headers: {
        'Accept': 'application/json',
      },
    }
  );

  if (!response.ok) {
    let errorDetail = `Failed to index repository for RAG (HTTP ${response.status})`;
    try {
      const errorJson = await response.json();
      if (errorJson && errorJson.detail) {
        errorDetail = typeof errorJson.detail === 'string' ? errorJson.detail : JSON.stringify(errorJson.detail);
      }
    } catch {
      // Fallback
    }
    throw new Error(errorDetail);
  }

  return response.json();
}

// 14. RAG Semantic Retrieval POST request
export async function retrieveRepositoryRAG(
  repoId: string,
  query: string,
  topK: number = 5,
  scoreThreshold: number = 0.0
): Promise<RepositoryRetrievalResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/repositories/${encodeURIComponent(repoId)}/retrieve`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify({
        query,
        top_k: topK,
        score_threshold: scoreThreshold,
      }),
    }
  );

  if (!response.ok) {
    let errorDetail = `Failed to execute semantic retrieval (HTTP ${response.status})`;
    try {
      const errorJson = await response.json();
      if (errorJson && errorJson.detail) {
        errorDetail = typeof errorJson.detail === 'string' ? errorJson.detail : JSON.stringify(errorJson.detail);
      }
    } catch {
      // Fallback
    }
    throw new Error(errorDetail);
  }

  return response.json();
}










