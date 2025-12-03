'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Card, CardContent } from '@/components/ui/card';

interface FuzzyMatchResults {
  total_freed: number;
  total_osmind: number;
  matched: number;
  unmatched_freed: number;
  tier_distribution: { [key: string]: number };
  confidence_stats: {
    avg: number;
    min: number;
    max: number;
  };
  low_confidence_count: number;
  all_matches_file: string;
  low_confidence_file: string | null;
  dry_run: boolean;
}

interface MatchingState {
  running: boolean;
  results: FuzzyMatchResults | null;
  error: string | null;
  progress: string;
  started_at: string | null;
  completed_at: string | null;
}

export function FuzzyMatchModal() {
  const [open, setOpen] = useState(false);
  const [state, setState] = useState<MatchingState>({
    running: false,
    results: null,
    error: null,
    progress: '',
    started_at: null,
    completed_at: null,
  });
  const [config, setConfig] = useState({
    minTier: 1,
    tierLimit: 7,
    autoMatchThreshold: 0.70,
    dryRun: false,
  });

  // Poll for status updates when matching is running
  useEffect(() => {
    if (!state.running) return;

    const interval = setInterval(async () => {
      try {
        const response = await fetch('http://localhost:8000/api/fuzzy-match/status');
        const data = await response.json();
        setState(data);
      } catch (error) {
        console.error('Failed to fetch status:', error);
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [state.running]);

  const startMatching = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/fuzzy-match/start', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          min_tier: config.minTier,
          tier_limit: config.tierLimit,
          auto_match_threshold: config.autoMatchThreshold,
          dry_run: config.dryRun,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to start matching');
      }

      setState({ ...state, running: true, progress: 'Starting...' });
    } catch (error) {
      console.error('Error starting fuzzy matching:', error);
      setState({ ...state, error: String(error) });
    }
  };

  const downloadFile = (filename: string) => {
    window.open(`http://localhost:8000/api/fuzzy-match/download/${filename}`, '_blank');
  };

  const renderTierDistribution = () => {
    if (!state.results) return null;

    const tierNames: { [key: string]: string } = {
      '1': 'Exact ID + Exact Date',
      '2': 'Exact ID + Date ±1',
      '3': 'Exact Name + Exact Date',
      '4': 'Fuzzy Name (>90%) + Exact Date',
      '5': 'Exact Name + Date ±1',
      '6': 'Fuzzy Name (>85%) + Date ±1',
      '7': 'Partial Name + Exact Date',
    };

    const totalMatches = state.results.matched;
    const tiers = Object.entries(state.results.tier_distribution)
      .sort(([a], [b]) => parseInt(a) - parseInt(b));

    return (
      <div className="space-y-2">
        <h4 className="font-medium text-sm">Match Distribution by Tier:</h4>
        {tiers.map(([tier, count]) => {
          const percentage = totalMatches > 0 ? (count / totalMatches * 100) : 0;
          return (
            <div key={tier} className="space-y-1">
              <div className="flex justify-between text-xs">
                <span className="text-muted-foreground">
                  Tier {tier}: {tierNames[tier]}
                </span>
                <span className="font-medium">{count} ({percentage.toFixed(1)}%)</span>
              </div>
              <Progress value={percentage} className="h-1" />
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="default" className="gap-2">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M16 3h5v5" />
            <path d="M8 3H3v5" />
            <path d="M12 22v-8" />
            <path d="M16 14 21 9" />
            <path d="M8 14 3 9" />
          </svg>
          Run Fuzzy Matching
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Fuzzy Note Matching</DialogTitle>
          <DialogDescription>
            Match Freed.ai notes with Osmind EHR notes using multi-tier fuzzy matching algorithm
          </DialogDescription>
        </DialogHeader>

        {!state.running && !state.results && !state.error && (
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Mode</Label>
              <div className="flex gap-2">
                <Button
                  variant={config.dryRun ? 'outline' : 'default'}
                  size="sm"
                  onClick={() => setConfig({ ...config, dryRun: false })}
                >
                  Live Run
                </Button>
                <Button
                  variant={config.dryRun ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setConfig({ ...config, dryRun: true })}
                >
                  Dry Run (Preview Only)
                </Button>
              </div>
            </div>

            <div className="space-y-2">
              <Label>Tier Range: {config.minTier} - {config.tierLimit}</Label>
              <p className="text-xs text-muted-foreground">
                Tier 1-2: Exact patient IDs | Tier 3-5: Name matching | Tier 6-7: Fuzzy/partial
              </p>
            </div>

            <div className="space-y-2">
              <Label>Auto-match Threshold: {(config.autoMatchThreshold * 100).toFixed(0)}%</Label>
              <p className="text-xs text-muted-foreground">
                Matches above this confidence will be auto-linked (below require manual review)
              </p>
            </div>

            <Card className="bg-muted/50">
              <CardContent className="pt-4 text-sm space-y-1">
                <p className="font-medium">Expected Results:</p>
                <ul className="list-disc list-inside text-muted-foreground space-y-0.5">
                  <li>~928 matches (69% of 1,340 Freed notes)</li>
                  <li>Processing time: ~45 seconds</li>
                  <li>CSV reports will be generated</li>
                </ul>
              </CardContent>
            </Card>
          </div>
        )}

        {state.running && (
          <div className="space-y-4 py-6">
            <div className="flex items-center justify-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
            </div>
            <div className="text-center space-y-2">
              <p className="font-medium">{state.progress}</p>
              <p className="text-sm text-muted-foreground">
                This may take 30-60 seconds...
              </p>
            </div>
          </div>
        )}

        {state.error && (
          <div className="bg-destructive/10 border border-destructive text-destructive px-4 py-3 rounded-md">
            <p className="font-medium">Error</p>
            <p className="text-sm">{state.error}</p>
          </div>
        )}

        {state.results && (
          <div className="space-y-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <Card>
                <CardContent className="pt-4">
                  <div className="text-2xl font-bold">{state.results.matched}</div>
                  <div className="text-xs text-muted-foreground">
                    Matched ({((state.results.matched / state.results.total_freed) * 100).toFixed(1)}%)
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-4">
                  <div className="text-2xl font-bold">{state.results.unmatched_freed}</div>
                  <div className="text-xs text-muted-foreground">Unmatched</div>
                </CardContent>
              </Card>
            </div>

            <div className="grid grid-cols-3 gap-2 text-sm">
              <div>
                <span className="text-muted-foreground">Avg Confidence:</span>
                <Badge variant="secondary" className="ml-2">
                  {(state.results.confidence_stats.avg * 100).toFixed(0)}%
                </Badge>
              </div>
              <div>
                <span className="text-muted-foreground">Min:</span>
                <Badge variant="outline" className="ml-2">
                  {(state.results.confidence_stats.min * 100).toFixed(0)}%
                </Badge>
              </div>
              <div>
                <span className="text-muted-foreground">Max:</span>
                <Badge variant="outline" className="ml-2">
                  {(state.results.confidence_stats.max * 100).toFixed(0)}%
                </Badge>
              </div>
            </div>

            {renderTierDistribution()}

            {state.results.low_confidence_count > 0 && (
              <Card className="bg-yellow-50 dark:bg-yellow-950/20 border-yellow-200 dark:border-yellow-900">
                <CardContent className="pt-4">
                  <p className="text-sm">
                    <span className="font-medium">{state.results.low_confidence_count}</span> low-confidence matches require manual review
                  </p>
                </CardContent>
              </Card>
            )}

            {state.results.dry_run && (
              <Card className="bg-blue-50 dark:bg-blue-950/20 border-blue-200 dark:border-blue-900">
                <CardContent className="pt-4">
                  <p className="text-sm font-medium">
                    Dry Run Complete - No database changes made
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    Run without Dry Run mode to create {state.results.matched} combined_notes records
                  </p>
                </CardContent>
              </Card>
            )}

            <div className="space-y-2">
              <Label>Download Reports:</Label>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => downloadFile(state.results!.all_matches_file)}
                >
                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  All Matches ({state.results.matched})
                </Button>
                {state.results.low_confidence_file && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => downloadFile(state.results!.low_confidence_file!)}
                  >
                    <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                    Low Confidence ({state.results.low_confidence_count})
                  </Button>
                )}
              </div>
            </div>
          </div>
        )}

        <DialogFooter>
          {!state.running && !state.results && (
            <>
              <Button variant="outline" onClick={() => setOpen(false)}>
                Cancel
              </Button>
              <Button onClick={startMatching}>
                {config.dryRun ? 'Run Dry Run' : 'Start Matching'}
              </Button>
            </>
          )}
          {state.results && (
            <Button onClick={() => {
              setState({
                running: false,
                results: null,
                error: null,
                progress: '',
                started_at: null,
                completed_at: null,
              });
              if (!state.results.dry_run) {
                // Reload page to show new data
                window.location.reload();
              }
            }}>
              Close
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
