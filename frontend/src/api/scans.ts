import api from './client';
import type { Scan, Vulnerability, Patch } from '../types';
export const fetchScans = async (): Promise<Scan[]> => { const { data } = await api.get('/scans'); return data; };
export const fetchScan = async (id: string): Promise<Scan> => { const { data } = await api.get(`/scans/${id}`); return data; };
export const fetchResults = async (scanId: string, severity?: string, filePath?: string): Promise<Vulnerability[]> => {
  const params: Record<string, string> = {};
  if (severity) params.severity = severity;
  if (filePath) params.file_path = filePath;
  const { data } = await api.get(`/scans/${scanId}/results`, { params }); return data;
};
export const fetchVulnerability = async (scanId: string, vulnId: string): Promise<Vulnerability> => { const { data } = await api.get(`/scans/${scanId}/results/${vulnId}`); return data; };
export const fetchPatches = async (scanId: string, vulnId: string): Promise<Patch[]> => { const { data } = await api.get(`/scans/${scanId}/results/${vulnId}/patches`); return data; };
export const createScan = async (sourceType: string, sourcePath: string): Promise<Scan> => { const { data } = await api.post('/scans', null, { params: { source_type: sourceType, source_path: sourcePath } }); return data; };
export const createScanFromZip = async (file: File): Promise<Scan> => { const fd = new FormData(); fd.append('file', file); const { data } = await api.post('/scans?source_type=local', fd); return data; };

export const generatePatches = async (scanId: string): Promise<{ generated: number; errors: number }> => {
  const { data } = await api.post(`/scans/${scanId}/patches/generate`);
  return data;
};

// ── GitHub Integration ──

interface GitHubIssueResult {
  vuln_id: string;
  issue_number?: number;
  url?: string;
  error?: string;
}

interface CreateIssuesResponse {
  scan_id: string;
  repo: string;
  results: GitHubIssueResult[];
}

export const createIssues = async (
  scanId: string,
  repo?: string,
  severity?: string,
): Promise<CreateIssuesResponse> => {
  const { data } = await api.post(`/scans/${scanId}/issues`, { repo, severity });
  return data;
};

export const createPR = async (
  scanId: string,
  repo?: string,
  branch?: string,
  base?: string,
): Promise<{ scan_id: string; repo: string; pr_url: string; pr_number: number }> => {
  const { data } = await api.post(`/scans/${scanId}/pr`, { repo, branch, base });
  return data;
};
