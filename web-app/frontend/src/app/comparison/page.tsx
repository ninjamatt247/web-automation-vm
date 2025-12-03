'use client';

import axios from 'axios';
import { RefreshCw } from 'lucide-react';
import { useEffect, useState } from 'react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { FuzzyMatchModal } from '@/components/FuzzyMatchModal';

interface KPIData {
  pipeline: {
    total_freed_notes: number;
    matched_notes: number;
    unmatched_freed: number;
  };
  match_quality: {
    high_confidence: number;
    medium_confidence: number;
    low_confidence: number;
    avg_confidence: number;
    tier_distribution: Record<string, number>;
    match_rate: number;
  };
}

export default function ComparisonPage() {
  const [kpis, setKpis] = useState<KPIData | null>(null);
  const [loading, setLoading] = useState(true);
  const [filterType, setFilterType] = useState('all');

  useEffect(() => {
    fetchKPIs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterType]);

  const fetchKPIs = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams({ filter_type: filterType });
      const response = await axios.get(`/api/kpis?${params}`);
      setKpis(response.data);
    } catch (err) {
      console.error('Failed to load match KPIs:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container mx-auto px-4 py-8 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-4xl font-bold tracking-tight">Note Matching</h1>
        <div className="flex items-center gap-4">
          <Select value={filterType} onValueChange={setFilterType}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Select period" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Time</SelectItem>
              <SelectItem value="week">Last Week</SelectItem>
              <SelectItem value="month">Last Month</SelectItem>
            </SelectContent>
          </Select>
          <Button onClick={fetchKPIs} variant="outline">
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
          <FuzzyMatchModal />
        </div>
      </div>

      {/* Match Analytics KPIs */}
      {!loading && kpis && (
        <>
          <div className="space-y-4">
            <h2 className="text-2xl font-bold tracking-tight">Match Performance</h2>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Total Notes</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{kpis.pipeline.total_freed_notes}</div>
                  <p className="text-xs text-muted-foreground mt-1">In Freed.ai</p>
                </CardContent>
              </Card>

              <Card className="border-blue-500/50">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Matched</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                    {kpis.pipeline.matched_notes}
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    {kpis.match_quality.match_rate}% match rate
                  </p>
                </CardContent>
              </Card>

              <Card className="border-red-500/50">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Unmatched</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-red-600 dark:text-red-400">
                    {kpis.pipeline.unmatched_freed}
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">Need matching</p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Avg Confidence</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {(kpis.match_quality.avg_confidence * 100).toFixed(1)}%
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">Overall quality</p>
                </CardContent>
              </Card>
            </div>
          </div>

          <div className="space-y-4">
            <h2 className="text-2xl font-bold tracking-tight">Match Quality Distribution</h2>
            <div className="grid gap-4 md:grid-cols-3">
              <Card className="border-green-500/50">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">High Confidence</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                    {kpis.match_quality.high_confidence}
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">≥90% confidence</p>
                </CardContent>
              </Card>

              <Card className="border-blue-500/50">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Medium Confidence</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                    {kpis.match_quality.medium_confidence}
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">70-89% confidence</p>
                </CardContent>
              </Card>

              <Card className="border-orange-500/50">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Low Confidence</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-orange-600 dark:text-orange-400">
                    {kpis.match_quality.low_confidence}
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">&lt;70% - needs review</p>
                </CardContent>
              </Card>
            </div>
          </div>

          <div className="space-y-4">
            <h2 className="text-2xl font-bold tracking-tight">Tier Distribution</h2>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              {Object.entries(kpis.match_quality.tier_distribution)
                .sort(([a], [b]) => a.localeCompare(b))
                .map(([tier, count]) => (
                  <Card key={tier}>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                      <CardTitle className="text-sm font-medium">{tier.replace('_', ' ')}</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="text-2xl font-bold">{count}</div>
                      <p className="text-xs text-muted-foreground mt-1">
                        {kpis.pipeline.matched_notes > 0
                          ? `${((count / kpis.pipeline.matched_notes) * 100).toFixed(1)}%`
                          : '0%'}
                      </p>
                    </CardContent>
                  </Card>
                ))}
            </div>
          </div>
        </>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Fuzzy Note Matching System</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-muted-foreground">
            Match Freed.ai notes with Osmind EHR notes using a 7-tier fuzzy matching algorithm.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
            <div className="space-y-2">
              <h3 className="font-semibold text-sm">Matching Tiers</h3>
              <ul className="text-sm text-muted-foreground space-y-1">
                <li><span className="font-medium">Tier 1-2:</span> Exact patient ID matching</li>
                <li><span className="font-medium">Tier 3:</span> Exact name + exact date</li>
                <li><span className="font-medium">Tier 4:</span> Fuzzy name (&gt;90%) + exact date</li>
                <li><span className="font-medium">Tier 5:</span> Exact name + date ±1 day</li>
                <li><span className="font-medium">Tier 6:</span> Fuzzy name (&gt;85%) + date ±1</li>
                <li><span className="font-medium">Tier 7:</span> Partial name + exact date</li>
              </ul>
            </div>

            <div className="space-y-2">
              <h3 className="font-semibold text-sm">Features</h3>
              <ul className="text-sm text-muted-foreground space-y-1">
                <li>✓ Multi-tier matching strategy</li>
                <li>✓ Confidence scoring (60-100%)</li>
                <li>✓ Auto-match with threshold control</li>
                <li>✓ Manual review for low-confidence matches</li>
                <li>✓ CSV export of all results</li>
                <li>✓ Dry run mode for testing</li>
              </ul>
            </div>
          </div>

          {kpis && (
            <div className="bg-muted/50 p-4 rounded-lg mt-4">
              <h3 className="font-semibold text-sm mb-2">Current Performance</h3>
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div>
                  <div className="text-2xl font-bold">{kpis.pipeline.matched_notes}</div>
                  <div className="text-muted-foreground">
                    Matches ({kpis.match_quality.match_rate}%)
                  </div>
                </div>
                <div>
                  <div className="text-2xl font-bold">~45s</div>
                  <div className="text-muted-foreground">Processing Time</div>
                </div>
                <div>
                  <div className="text-2xl font-bold">
                    {(kpis.match_quality.avg_confidence * 100).toFixed(0)}%
                  </div>
                  <div className="text-muted-foreground">Avg Confidence</div>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
