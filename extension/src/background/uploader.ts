import { browser } from 'wxt/browser';
import { getPackage } from '@/src/lib/storage';

export interface UploadResult {
  status: 'uploaded';
  packageId: string;
  sessionId: string;
  sizeBytes: number;
  replayUrl: string;
}

interface SessionUploadResponse {
  id: string;
  status: string;
  size_bytes: number;
  event_count: number;
  replay_url: string;
}

const API_BASE_URL_KEY = 'rebug.apiBaseUrl';
const DEFAULT_API_BASE_URL = 'http://localhost:8000/api/v1';

export async function uploadSessionPackage(packageId: string): Promise<UploadResult> {
  const packageRecord = await getPackage(packageId);
  if (!packageRecord) {
    throw new Error(`Package not found: ${packageId}`);
  }

  const apiBaseUrl = await getApiBaseUrl();
  const uploadBody = packageRecord.data.slice().buffer as ArrayBuffer;
  const response = await fetch(`${apiBaseUrl}/sessions`, {
    method: 'POST',
    headers: {
      'content-type': 'application/octet-stream',
    },
    body: new Blob([uploadBody], {
      type: 'application/octet-stream',
    }),
  });

  if (!response.ok) {
    throw new Error(`Upload failed: ${response.status} ${await response.text()}`);
  }

  const upload = (await response.json()) as SessionUploadResponse;

  return {
    status: 'uploaded',
    packageId,
    sessionId: upload.id,
    sizeBytes: upload.size_bytes,
    replayUrl: upload.replay_url,
  };
}

async function getApiBaseUrl(): Promise<string> {
  const stored = await browser.storage.local.get(API_BASE_URL_KEY);
  const value = stored[API_BASE_URL_KEY];
  return typeof value === 'string' && value ? value.replace(/\/$/, '') : DEFAULT_API_BASE_URL;
}
