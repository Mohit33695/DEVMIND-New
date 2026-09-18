import type { RepositoryUploadResponse, RepositoryScanResult } from '@/types/repository';

export type { RepositoryUploadResponse, RepositoryScanResult };

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
