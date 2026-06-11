import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box, Typography, Card, CardContent, List, ListItem, ListItemButton,
  ListItemText, Chip, Button, Dialog, DialogTitle, DialogContent,
  DialogActions, TextField, Select, MenuItem, FormControl, InputLabel,
  Stack, Divider, Alert, Snackbar, Link, IconButton, Collapse,
} from '@mui/material';
import {
  GitHub as GitHubIcon, OpenInNew as OpenInNewIcon,
  BugReport as BugIcon, ExpandMore as ExpandIcon,
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { fetchScan, fetchResults, createIssues, createPR, generatePatches } from '../api/scans';
import SeverityBadge from '../components/SeverityBadge';

const ScanResult: React.FC = () => {
  const { scanId } = useParams<{ scanId: string }>();
  const navigate = useNavigate();
  const { t } = useTranslation();

  const { data: scan } = useQuery({
    queryKey: ['scan', scanId],
    queryFn: () => fetchScan(scanId!),
    enabled: !!scanId,
  });
  const { data: vulns } = useQuery({
    queryKey: ['results', scanId],
    queryFn: () => fetchResults(scanId!),
    enabled: !!scanId,
  });

  // GitHub issue dialog state
  const [issueDialogOpen, setIssueDialogOpen] = useState(false);
  const [issueRepo, setIssueRepo] = useState('');
  const [issueSeverity, setIssueSeverity] = useState('');

  // GitHub PR dialog state
  const [prDialogOpen, setPrDialogOpen] = useState(false);
  const [prRepo, setPrRepo] = useState('');
  const [prBranch, setPrBranch] = useState('vulnscout-fix');
  const [prBase, setPrBase] = useState('main');

  // Patch generation
  const [patchLoading, setPatchLoading] = useState(false);
  const [patchResult, setPatchResult] = useState<{ generated: number; errors: number } | null>(null);

  // Loading & results
  const [issueLoading, setIssueLoading] = useState(false);
  const [prLoading, setPrLoading] = useState(false);
  const [issueResults, setIssueResults] = useState<any[] | null>(null);
  const [prResult, setPrResult] = useState<{ pr_url: string; pr_number: number } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showResults, setShowResults] = useState(false);

  // Guess repo from scan source
  React.useEffect(() => {
    if (scan?.source_path) {
      const guess = scan.source_path.replace(/\.git$/, '');
      setIssueRepo(guess);
      setPrRepo(guess);
    }
  }, [scan]);

  if (!scan || !vulns) return <Typography>{t('common.loading')}</Typography>;

  // ── Issue handlers ──
  const handleCreateIssues = async () => {
    setIssueLoading(true);
    setError(null);
    setIssueResults(null);
    try {
      const res = await createIssues(scanId!, issueRepo || undefined, issueSeverity || undefined);
      setIssueResults(res.results);
      setShowResults(true);
      setIssueDialogOpen(false);
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || 'Failed to create issues');
    } finally {
      setIssueLoading(false);
    }
  };

  const handleGeneratePatches = async () => {
    setPatchLoading(true);
    setError(null);
    setPatchResult(null);
    try {
      const res = await generatePatches(scanId!);
      setPatchResult(res);
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || 'Failed to generate patches');
    } finally {
      setPatchLoading(false);
    }
  };

  const handleCreatePR = async () => {
    setPrLoading(true);
    setError(null);
    setPrResult(null);
    try {
      const res = await createPR(scanId!, prRepo || undefined, prBranch, prBase);
      setPrResult({ pr_url: res.pr_url, pr_number: res.pr_number });
      setShowResults(true);
      setPrDialogOpen(false);
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || 'Failed to create PR');
    } finally {
      setPrLoading(false);
    }
  };

  const isGitHubSource = scan.source_path?.includes('github.com');
  const hasVulns = vulns.length > 0;
  const totalCritical = vulns.filter(v => v.severity === 'critical').length;
  const totalHigh = vulns.filter(v => v.severity === 'high').length;
  const totalMedium = vulns.filter(v => v.severity === 'medium').length;
  const totalLow = vulns.filter(v => v.severity === 'low').length;

  return (
    <Box>
      {/* ── Header ── */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 3, flexWrap: 'wrap', gap: 1 }}>
        <Box>
          <Typography variant="h4" fontWeight={600}>{t('scan.results')}</Typography>
          <Typography color="text.secondary" variant="body2">
            {scan.source_path} — {scan.scanned_files}/{scan.total_files} files
            {isGitHubSource && (
              <Chip icon={<GitHubIcon />} label="GitHub" size="small" variant="outlined" sx={{ ml: 1 }} />
            )}
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
          <Chip
            label={scan.status}
            color={scan.status === 'done' ? 'success' : scan.status === 'failed' ? 'error' : 'default'}
          />
        </Box>
      </Box>

      {/* ── Severity Summary ── */}
      <Card elevation={0} sx={{ border: '1px solid', borderColor: 'divider', mb: 3 }}>
        <CardContent>
          <Box sx={{ display: 'flex', gap: 3, flexWrap: 'wrap' }}>
            {totalCritical > 0 && (
              <Box sx={{ textAlign: 'center' }}>
                <Typography variant="h4" color="error" fontWeight={700}>{totalCritical}</Typography>
                <SeverityBadge severity="critical" />
              </Box>
            )}
            {totalHigh > 0 && (
              <Box sx={{ textAlign: 'center' }}>
                <Typography variant="h4" color="warning.dark" fontWeight={700}>{totalHigh}</Typography>
                <SeverityBadge severity="high" />
              </Box>
            )}
            {totalMedium > 0 && (
              <Box sx={{ textAlign: 'center' }}>
                <Typography variant="h4" color="warning.main" fontWeight={700}>{totalMedium}</Typography>
                <SeverityBadge severity="medium" />
              </Box>
            )}
            {totalLow > 0 && (
              <Box sx={{ textAlign: 'center' }}>
                <Typography variant="h4" fontWeight={700}>{totalLow}</Typography>
                <SeverityBadge severity="low" />
              </Box>
            )}
            {!hasVulns && <Typography color="text.secondary">No vulnerabilities found.</Typography>}
          </Box>
        </CardContent>
      </Card>

      {/* ── Vulnerability List ── */}
      {hasVulns && (
        <Card elevation={0} sx={{ border: '1px solid', borderColor: 'divider', mb: 3 }}>
          <CardContent>
            <Typography variant="h6" fontWeight={600} sx={{ mb: 2 }}>Vulnerabilities ({vulns.length})</Typography>
            <List disablePadding>
              {vulns.map(v => (
                <ListItem key={v.id} disablePadding divider>
                  <ListItemButton onClick={() => navigate(`/scans/${scanId}/vulns/${v.id}`)}>
                    <SeverityBadge severity={v.severity} />
                    <ListItemText
                      sx={{ ml: 2 }}
                      primary={v.title}
                      secondary={`${v.file_path}:${v.line_start || '?'}`}
                      primaryTypographyProps={{ variant: 'body2', fontWeight: 500 }}
                    />
                  </ListItemButton>
                </ListItem>
              ))}
            </List>
          </CardContent>
        </Card>
      )}

      {/* ── GitHub Integration ── */}
      <Card elevation={0} sx={{ border: '1px solid', borderColor: 'divider' }}>
        <CardContent>
          <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 2 }}>
            <GitHubIcon color="primary" />
            <Typography variant="h6" fontWeight={600}>{t('github.title')}</Typography>
          </Stack>

          {hasVulns ? (
            <Stack direction="row" spacing={2} flexWrap="wrap" alignItems="center">
              <Button
                variant="outlined"
                startIcon={<BugIcon />}
                onClick={() => setIssueDialogOpen(true)}
                disabled={issueLoading}
              >
                {t('github.createIssues')}
              </Button>
              <Button
                variant="outlined"
                onClick={handleGeneratePatches}
                disabled={patchLoading}
              >
                {patchLoading ? t('github.generatingPatches') : t('github.generatePatches')}
              </Button>
              <Button
                variant="contained"
                startIcon={<GitHubIcon />}
                onClick={() => setPrDialogOpen(true)}
                disabled={prLoading}
              >
                {t('github.createPR')}
              </Button>
              {patchResult && (
                <Chip
                  label={t('github.patchesGenerated', { count: patchResult.generated, errors: patchResult.errors })}
                  color={patchResult.errors > 0 ? 'warning' : 'success'}
                  size="small"
                />
              )}
            </Stack>
          ) : (
            <Typography variant="body2" color="text.secondary">
              No vulnerabilities to report to GitHub.
            </Typography>
          )}

          {/* ── Results Display ── */}
          {(issueResults || prResult || patchResult) && (
            <>
              <Divider sx={{ my: 2 }} />
              <Box
                sx={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 0.5 }}
                onClick={() => setShowResults(!showResults)}
              >
                <Typography variant="subtitle2" fontWeight={600}>{t('github.results')}</Typography>
                <ExpandIcon
                  sx={{ transform: showResults ? 'rotate(180deg)' : 'none', transition: '0.2s', fontSize: 18 }}
                />
              </Box>
              <Collapse in={showResults}>
                {issueResults && (
                  <Box sx={{ mt: 1 }}>
                    {issueResults.map(r => (
                      <Box key={r.vuln_id} sx={{ display: 'flex', alignItems: 'center', gap: 1, py: 0.5 }}>
                        {r.url ? (
                          <Link href={r.url} target="_blank" rel="noopener" underline="hover" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                            <Chip label={t('github.issueCreated', { number: r.issue_number })} size="small" color="success" />
                            <OpenInNewIcon fontSize="inherit" />
                          </Link>
                        ) : (
                          <Chip label={`Failed: ${r.error}`} size="small" color="error" />
                        )}
                      </Box>
                    ))}
                  </Box>
                )}
                {prResult && (
                  <Box sx={{ mt: 1 }}>
                    {prResult.pr_url ? (
                      <Link href={prResult.pr_url} target="_blank" rel="noopener" underline="hover" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        <Chip label={t('github.prCreated', { number: prResult.pr_number })} size="small" color="success" />
                        <OpenInNewIcon fontSize="inherit" />
                      </Link>
                    ) : (
                      <Chip label="PR creation failed" size="small" color="error" />
                    )}
                  </Box>
                )}
              </Collapse>
            </>
          )}
        </CardContent>
      </Card>

      {/* ── Create Issues Dialog ── */}
      <Dialog open={issueDialogOpen} onClose={() => !issueLoading && setIssueDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{t('github.createIssues')}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField
              fullWidth
              label={t('github.repo')}
              value={issueRepo}
              onChange={e => setIssueRepo(e.target.value)}
              helperText={t('github.repoHint')}
              size="small"
              placeholder="owner/repo"
            />
            <FormControl fullWidth size="small">
              <InputLabel>{t('github.severity')}</InputLabel>
              <Select
                value={issueSeverity}
                label={t('github.severity')}
                onChange={e => setIssueSeverity(e.target.value)}
              >
                <MenuItem value="">All severities</MenuItem>
                <MenuItem value="critical">Critical only</MenuItem>
                <MenuItem value="high">High+</MenuItem>
                <MenuItem value="medium">Medium+</MenuItem>
                <MenuItem value="low">Low+</MenuItem>
              </Select>
            </FormControl>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setIssueDialogOpen(false)} disabled={issueLoading}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleCreateIssues}
            disabled={issueLoading || !issueRepo.trim()}
          >
            {issueLoading ? t('github.creating') : t('github.createIssues')}
          </Button>
        </DialogActions>
      </Dialog>

      {/* ── Create PR Dialog ── */}
      <Dialog open={prDialogOpen} onClose={() => !prLoading && setPrDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{t('github.createPR')}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField
              fullWidth
              label={t('github.repo')}
              value={prRepo}
              onChange={e => setPrRepo(e.target.value)}
              helperText={t('github.repoHint')}
              size="small"
              placeholder="owner/repo"
            />
            <TextField
              fullWidth
              label={t('github.branch')}
              value={prBranch}
              onChange={e => setPrBranch(e.target.value)}
              size="small"
            />
            <TextField
              fullWidth
              label={t('github.base')}
              value={prBase}
              onChange={e => setPrBase(e.target.value)}
              size="small"
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPrDialogOpen(false)} disabled={prLoading}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleCreatePR}
            disabled={prLoading || !prRepo.trim()}
          >
            {prLoading ? t('github.creating') : t('github.createPR')}
          </Button>
        </DialogActions>
      </Dialog>

      {/* ── Error Snackbar ── */}
      <Snackbar
        open={!!error}
        autoHideDuration={5000}
        onClose={() => setError(null)}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
      >
        <Alert severity="error" onClose={() => setError(null)} variant="filled">
          {error}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default ScanResult;
