export interface Scan {
  id: string;
  status: 'pending' | 'running' | 'done' | 'failed';
  source_type: 'local' | 'url' | 'cli';
  source_path: string;
  language: string | null;
  total_files: number;
  scanned_files: number;
  vuln_count_critical: number;
  vuln_count_high: number;
  vuln_count_medium: number;
  vuln_count_low: number;
  progress_percent: number;
  created_at: string;
}

export interface Vulnerability {
  id: string;
  scan_id: string;
  file_path: string;
  line_start: number | null;
  line_end: number | null;
  cwe_id: string | null;
  severity: 'critical' | 'high' | 'medium' | 'low';
  title: string | null;
  description: string | null;
  vulnerable_code: string | null;
}

export interface Patch {
  id: string;
  vuln_id: string;
  diff_content: string | null;
  description: string | null;
  status: 'draft' | 'applied' | 'rejected';
}

export interface ScanProgressMessage {
  type: 'progress' | 'vuln_found' | 'file_done' | 'scan_done';
  percent?: number;
  current_file?: string;
  file?: string;
  severity?: string;
  title?: string;
  total_vulns?: number;
  duration?: number;
}
