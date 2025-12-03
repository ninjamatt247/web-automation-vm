'use client';

import axios from 'axios';
import { ArrowDown, ArrowUp, Download, Mic, RefreshCw, TrendingDown, TrendingUp } from 'lucide-react';
import { useEffect, useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

interface Stats {
  total_processed?: number;
  total_in_freed?: number;
  complete_in_osmind?: number;
  missing_from_osmind?: number;
  incomplete_in_osmind?: number;
  to_process?: number;
  comparison_timestamp?: string;
}

interface KPIData {
  date_range: {
    filter_type: string;
    start: string | null;
    end: string | null;
  };
  pipeline: {
    total_freed_notes: number;
    matched_notes: number;
    ai_processed: number;
    uploaded_to_osmind: number;
    pending_processing: number;
    requiring_review: number;
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
  ai_processing: {
    total_processed: number;
    success_rate: number;
    intervention_rate: number;
    critical_failures: number;
    avg_tokens: number;
    avg_processing_ms: number;
  };
  clinical: {
    notes_per_patient: number;
    signed_notes: number;
    avg_note_length_freed: number;
    avg_note_length_osmind: number;
    unique_patients: number;
  };
  efficiency: {
    completion_rate: number;
    match_success_rate: number;
  };
}

interface FetchMessage {
  type: 'success' | 'error';
  text: string;
}

export default function DashboardPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [kpis, setKpis] = useState<KPIData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterType, setFilterType] = useState('all');
  const [isVoiceActive, setIsVoiceActive] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [fetchingFreed, setFetchingFreed] = useState(false);
  const [fetchingOsmind, setFetchingOsmind] = useState(false);
  const [fetchMessage, setFetchMessage] = useState<FetchMessage | null>(null);

  useEffect(() => {
    fetchStats();
    fetchKPIs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterType]);

  const fetchStats = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams({ filter_type: filterType });
      const response = await axios.get(`/api/stats?${params}`);
      setStats(response.data);
      setError(null);
    } catch (err) {
      setError('Failed to load statistics');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const fetchKPIs = async () => {
    try {
      const params = new URLSearchParams({ filter_type: filterType });
      const response = await axios.get(`/api/kpis?${params}`);
      setKpis(response.data);
    } catch (err) {
      console.error('Failed to load KPIs:', err);
    }
  };

  const handleFetchFromFreed = async () => {
    try {
      setFetchingFreed(true);
      setFetchMessage(null);
      const response = await axios.post('/api/fetch-from-freed', { days: 90 });
      setFetchMessage({
        type: 'success',
        text: response.data.message,
      });
      setTimeout(() => {
        fetchStats();
      }, 5000);
    } catch (err) {
      const error = err as { response?: { data?: { detail?: string } } };
      setFetchMessage({
        type: 'error',
        text: error.response?.data?.detail || 'Failed to fetch from Freed.ai',
      });
      console.error(err);
    } finally {
      setFetchingFreed(false);
    }
  };

  const handleFetchFromOsmind = async () => {
    try {
      setFetchingOsmind(true);
      setFetchMessage(null);
      const response = await axios.post('/api/fetch-from-osmind');
      setFetchMessage({
        type: 'success',
        text: response.data.message,
      });
      setTimeout(() => {
        fetchStats();
      }, 5000);
    } catch (err) {
      const error = err as { response?: { data?: { detail?: string } } };
      setFetchMessage({
        type: 'error',
        text: error.response?.data?.detail || 'Failed to fetch from Osmind',
      });
      console.error(err);
    } finally {
      setFetchingOsmind(false);
    }
  };

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="bg-destructive/10 text-destructive rounded-lg p-4">
          {error}
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8 space-y-6">
      <div className="flex flex-col gap-4">
        <h1 className="text-4xl font-bold tracking-tight">Dashboard</h1>

        <div className="flex items-center gap-4">
          <label className="text-sm font-medium">Filter by:</label>
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
          <Button onClick={() => { fetchStats(); fetchKPIs(); }} className="ml-auto" variant="outline">
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Comprehensive KPI Sections */}
      {kpis && (
        <div className="space-y-8">
          {/* Pipeline Metrics */}
          <div className="space-y-4">
            <h2 className="text-2xl font-bold tracking-tight">Processing Pipeline</h2>
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                  <Card className="@container/card">
                    <CardHeader>
                      <CardDescription>Total Notes</CardDescription>
                      <CardTitle className="text-2xl font-semibold tabular-nums @[250px]/card:text-3xl">
                        {kpis.pipeline.total_freed_notes.toLocaleString()}
                      </CardTitle>
                      <CardAction>
                        <Badge variant="outline">
                          <TrendingUp className="h-3 w-3 mr-1" />
                          Active
                        </Badge>
                      </CardAction>
                    </CardHeader>
                    <CardFooter className="flex-col items-start gap-1.5 text-sm">
                      <div className="line-clamp-1 flex gap-2 font-medium">
                        In Freed.ai system
                      </div>
                      <div className="text-muted-foreground">
                        Source notes awaiting processing
                      </div>
                    </CardFooter>
                  </Card>

                  <Card className="@container/card">
                    <CardHeader>
                      <CardDescription>Matched Notes</CardDescription>
                      <CardTitle className="text-2xl font-semibold tabular-nums text-blue-600 dark:text-blue-400 @[250px]/card:text-3xl">
                        {kpis.pipeline.matched_notes.toLocaleString()}
                      </CardTitle>
                      <CardAction>
                        <Badge variant="outline" className="text-blue-600 dark:text-blue-400">
                          <TrendingUp className="h-3 w-3 mr-1" />
                          {kpis.match_quality.match_rate}%
                        </Badge>
                      </CardAction>
                    </CardHeader>
                    <CardFooter className="flex-col items-start gap-1.5 text-sm">
                      <div className="line-clamp-1 flex gap-2 font-medium">
                        Strong match rate <TrendingUp className="h-4 w-4" />
                      </div>
                      <div className="text-muted-foreground">
                        Successfully linked with Osmind
                      </div>
                    </CardFooter>
                  </Card>

                  <Card className="@container/card">
                    <CardHeader>
                      <CardDescription>AI Processed</CardDescription>
                      <CardTitle className="text-2xl font-semibold tabular-nums text-purple-600 dark:text-purple-400 @[250px]/card:text-3xl">
                        {kpis.pipeline.ai_processed.toLocaleString()}
                      </CardTitle>
                      <CardAction>
                        <Badge variant="outline" className="text-purple-600 dark:text-purple-400">
                          Enhanced
                        </Badge>
                      </CardAction>
                    </CardHeader>
                    <CardFooter className="flex-col items-start gap-1.5 text-sm">
                      <div className="line-clamp-1 flex gap-2 font-medium">
                        AI enhancement complete
                      </div>
                      <div className="text-muted-foreground">
                        Multi-step processing pipeline
                      </div>
                    </CardFooter>
                  </Card>

                  <Card className="@container/card">
                    <CardHeader>
                      <CardDescription>Uploaded to Osmind</CardDescription>
                      <CardTitle className="text-2xl font-semibold tabular-nums text-green-600 dark:text-green-400 @[250px]/card:text-3xl">
                        {kpis.pipeline.uploaded_to_osmind.toLocaleString()}
                      </CardTitle>
                      <CardAction>
                        <Badge variant="outline" className="text-green-600 dark:text-green-400">
                          <TrendingUp className="h-3 w-3 mr-1" />
                          {kpis.efficiency.completion_rate}%
                        </Badge>
                      </CardAction>
                    </CardHeader>
                    <CardFooter className="flex-col items-start gap-1.5 text-sm">
                      <div className="line-clamp-1 flex gap-2 font-medium">
                        End-to-end completion <TrendingUp className="h-4 w-4" />
                      </div>
                      <div className="text-muted-foreground">
                        Successfully synced to EHR
                      </div>
                    </CardFooter>
                  </Card>
                </div>

                <div className="grid gap-4 md:grid-cols-3">
                  <Card className="@container/card">
                    <CardHeader>
                      <CardDescription>Pending Processing</CardDescription>
                      <CardTitle className="text-2xl font-semibold tabular-nums text-yellow-600 dark:text-yellow-400 @[250px]/card:text-3xl">
                        {kpis.pipeline.pending_processing.toLocaleString()}
                      </CardTitle>
                      <CardAction>
                        <Badge variant="outline" className="text-yellow-600 dark:text-yellow-400">
                          Queued
                        </Badge>
                      </CardAction>
                    </CardHeader>
                    <CardFooter className="flex-col items-start gap-1.5 text-sm">
                      <div className="line-clamp-1 flex gap-2 font-medium">
                        Awaiting AI processing
                      </div>
                      <div className="text-muted-foreground">
                        Next in enhancement pipeline
                      </div>
                    </CardFooter>
                  </Card>

                  <Card className="@container/card">
                    <CardHeader>
                      <CardDescription>Needs Review</CardDescription>
                      <CardTitle className="text-2xl font-semibold tabular-nums text-orange-600 dark:text-orange-400 @[250px]/card:text-3xl">
                        {kpis.pipeline.requiring_review.toLocaleString()}
                      </CardTitle>
                      <CardAction>
                        <Badge variant="outline" className="text-orange-600 dark:text-orange-400">
                          Action Required
                        </Badge>
                      </CardAction>
                    </CardHeader>
                    <CardFooter className="flex-col items-start gap-1.5 text-sm">
                      <div className="line-clamp-1 flex gap-2 font-medium">
                        Manual intervention needed
                      </div>
                      <div className="text-muted-foreground">
                        Low confidence matches
                      </div>
                    </CardFooter>
                  </Card>

                  <Card className="@container/card">
                    <CardHeader>
                      <CardDescription>Unmatched Notes</CardDescription>
                      <CardTitle className="text-2xl font-semibold tabular-nums text-red-600 dark:text-red-400 @[250px]/card:text-3xl">
                        {kpis.pipeline.unmatched_freed.toLocaleString()}
                      </CardTitle>
                      <CardAction>
                        <Badge variant="outline" className="text-red-600 dark:text-red-400">
                          <TrendingDown className="h-3 w-3 mr-1" />
                          No Match
                        </Badge>
                      </CardAction>
                    </CardHeader>
                    <CardFooter className="flex-col items-start gap-1.5 text-sm">
                      <div className="line-clamp-1 flex gap-2 font-medium">
                        No Osmind counterpart
                      </div>
                      <div className="text-muted-foreground">
                        May need manual matching
                      </div>
                    </CardFooter>
                  </Card>
                </div>
              </div>

            {/* Match Quality Metrics */}
            <div className="space-y-4">
                <h2 className="text-2xl font-bold tracking-tight">Match Quality</h2>
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                  <Card className="@container/card">
                    <CardHeader>
                      <CardDescription>High Confidence</CardDescription>
                      <CardTitle className="text-2xl font-semibold tabular-nums text-green-600 dark:text-green-400 @[250px]/card:text-3xl">
                        {kpis.match_quality.high_confidence.toLocaleString()}
                      </CardTitle>
                      <CardAction>
                        <Badge variant="outline" className="text-green-600 dark:text-green-400">
                          <TrendingUp className="h-3 w-3 mr-1" />
                          ≥90%
                        </Badge>
                      </CardAction>
                    </CardHeader>
                    <CardFooter className="flex-col items-start gap-1.5 text-sm">
                      <div className="line-clamp-1 flex gap-2 font-medium">
                        Excellent match quality
                      </div>
                      <div className="text-muted-foreground">
                        Strong AI confidence scores
                      </div>
                    </CardFooter>
                  </Card>

                  <Card className="@container/card">
                    <CardHeader>
                      <CardDescription>Medium Confidence</CardDescription>
                      <CardTitle className="text-2xl font-semibold tabular-nums text-blue-600 dark:text-blue-400 @[250px]/card:text-3xl">
                        {kpis.match_quality.medium_confidence.toLocaleString()}
                      </CardTitle>
                      <CardAction>
                        <Badge variant="outline" className="text-blue-600 dark:text-blue-400">
                          70-89%
                        </Badge>
                      </CardAction>
                    </CardHeader>
                    <CardFooter className="flex-col items-start gap-1.5 text-sm">
                      <div className="line-clamp-1 flex gap-2 font-medium">
                        Good match quality
                      </div>
                      <div className="text-muted-foreground">
                        Acceptable confidence range
                      </div>
                    </CardFooter>
                  </Card>

                  <Card className="@container/card">
                    <CardHeader>
                      <CardDescription>Low Confidence</CardDescription>
                      <CardTitle className="text-2xl font-semibold tabular-nums text-orange-600 dark:text-orange-400 @[250px]/card:text-3xl">
                        {kpis.match_quality.low_confidence.toLocaleString()}
                      </CardTitle>
                      <CardAction>
                        <Badge variant="outline" className="text-orange-600 dark:text-orange-400">
                          <TrendingDown className="h-3 w-3 mr-1" />
                          &lt;70%
                        </Badge>
                      </CardAction>
                    </CardHeader>
                    <CardFooter className="flex-col items-start gap-1.5 text-sm">
                      <div className="line-clamp-1 flex gap-2 font-medium">
                        Needs verification
                      </div>
                      <div className="text-muted-foreground">
                        May require manual review
                      </div>
                    </CardFooter>
                  </Card>

                  <Card className="@container/card">
                    <CardHeader>
                      <CardDescription>Avg Confidence</CardDescription>
                      <CardTitle className="text-2xl font-semibold tabular-nums @[250px]/card:text-3xl">
                        {(kpis.match_quality.avg_confidence * 100).toFixed(1)}%
                      </CardTitle>
                      <CardAction>
                        <Badge variant="outline">
                          <TrendingUp className="h-3 w-3 mr-1" />
                          Quality
                        </Badge>
                      </CardAction>
                    </CardHeader>
                    <CardFooter className="flex-col items-start gap-1.5 text-sm">
                      <div className="line-clamp-1 flex gap-2 font-medium">
                        Overall match quality
                      </div>
                      <div className="text-muted-foreground">
                        Across all matched notes
                      </div>
                    </CardFooter>
                  </Card>
                </div>
              </div>

            {/* Clinical Metrics */}
            <div className="space-y-4">
                <h2 className="text-2xl font-bold tracking-tight">Clinical Metrics</h2>
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
                  <Card className="@container/card">
                    <CardHeader>
                      <CardDescription>Unique Patients</CardDescription>
                      <CardTitle className="text-2xl font-semibold tabular-nums @[250px]/card:text-3xl">
                        {kpis.clinical.unique_patients.toLocaleString()}
                      </CardTitle>
                      <CardAction>
                        <Badge variant="outline">
                          Total
                        </Badge>
                      </CardAction>
                    </CardHeader>
                    <CardFooter className="flex-col items-start gap-1.5 text-sm">
                      <div className="line-clamp-1 flex gap-2 font-medium">
                        Patient population
                      </div>
                      <div className="text-muted-foreground">
                        Distinct individuals served
                      </div>
                    </CardFooter>
                  </Card>

                  <Card className="@container/card">
                    <CardHeader>
                      <CardDescription>Notes per Patient</CardDescription>
                      <CardTitle className="text-2xl font-semibold tabular-nums @[250px]/card:text-3xl">
                        {kpis.clinical.notes_per_patient.toFixed(1)}
                      </CardTitle>
                      <CardAction>
                        <Badge variant="outline">
                          Avg
                        </Badge>
                      </CardAction>
                    </CardHeader>
                    <CardFooter className="flex-col items-start gap-1.5 text-sm">
                      <div className="line-clamp-1 flex gap-2 font-medium">
                        Visit frequency
                      </div>
                      <div className="text-muted-foreground">
                        Average encounters per patient
                      </div>
                    </CardFooter>
                  </Card>

                  <Card className="@container/card">
                    <CardHeader>
                      <CardDescription>Signed Notes</CardDescription>
                      <CardTitle className="text-2xl font-semibold tabular-nums text-green-600 dark:text-green-400 @[250px]/card:text-3xl">
                        {kpis.clinical.signed_notes.toLocaleString()}
                      </CardTitle>
                      <CardAction>
                        <Badge variant="outline" className="text-green-600 dark:text-green-400">
                          <TrendingUp className="h-3 w-3 mr-1" />
                          Finalized
                        </Badge>
                      </CardAction>
                    </CardHeader>
                    <CardFooter className="flex-col items-start gap-1.5 text-sm">
                      <div className="line-clamp-1 flex gap-2 font-medium">
                        Provider-approved
                      </div>
                      <div className="text-muted-foreground">
                        Legally finalized documentation
                      </div>
                    </CardFooter>
                  </Card>

                  <Card className="@container/card">
                    <CardHeader>
                      <CardDescription>Avg Length (Freed)</CardDescription>
                      <CardTitle className="text-2xl font-semibold tabular-nums @[250px]/card:text-3xl">
                        {kpis.clinical.avg_note_length_freed.toLocaleString()}
                      </CardTitle>
                      <CardAction>
                        <Badge variant="outline">
                          Source
                        </Badge>
                      </CardAction>
                    </CardHeader>
                    <CardFooter className="flex-col items-start gap-1.5 text-sm">
                      <div className="line-clamp-1 flex gap-2 font-medium">
                        Original note size
                      </div>
                      <div className="text-muted-foreground">
                        Characters in Freed.ai notes
                      </div>
                    </CardFooter>
                  </Card>

                  <Card className="@container/card">
                    <CardHeader>
                      <CardDescription>Avg Length (Osmind)</CardDescription>
                      <CardTitle className="text-2xl font-semibold tabular-nums @[250px]/card:text-3xl">
                        {kpis.clinical.avg_note_length_osmind.toLocaleString()}
                      </CardTitle>
                      <CardAction>
                        <Badge variant="outline">
                          Enhanced
                        </Badge>
                      </CardAction>
                    </CardHeader>
                    <CardFooter className="flex-col items-start gap-1.5 text-sm">
                      <div className="line-clamp-1 flex gap-2 font-medium">
                        AI-enhanced size
                      </div>
                      <div className="text-muted-foreground">
                        Characters in Osmind EHR
                      </div>
                    </CardFooter>
                  </Card>
                </div>
              </div>
            </div>
      )}

      {stats && stats.comparison_timestamp && (
        <p className="text-sm text-muted-foreground">
          Last comparison: {(() => {
            try {
              const date = new Date(stats.comparison_timestamp);
              return isNaN(date.getTime()) ? 'Never' : date.toLocaleString();
            } catch {
              return 'Never';
            }
          })()}
        </p>
      )}

      {/* Voice Assistant Button */}
      <div className="space-y-6">
        {stats && (
          <>
          <div className="flex justify-center py-8">
            <Button
              size="lg"
              onClick={() => setIsModalOpen(true)}
              className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700"
            >
              <Mic className="w-5 h-5 mr-2" />
              Open Voice Assistant
            </Button>
          </div>

          {fetchMessage && (
            <div
              className={`rounded-lg p-4 ${
                fetchMessage.type === 'success'
                  ? 'bg-green-50 dark:bg-green-950 text-green-800 dark:text-green-200 border border-green-200 dark:border-green-800'
                  : 'bg-red-50 dark:bg-red-950 text-red-800 dark:text-red-200 border border-red-200 dark:border-red-800'
              }`}
            >
              {fetchMessage.text}
            </div>
          )}

          {/* Data Sync Section */}
          <Card>
            <CardHeader>
              <CardTitle>Data Sync</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex flex-wrap gap-4">
                <Button
                  onClick={handleFetchFromFreed}
                  disabled={fetchingFreed}
                  className="bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700"
                >
                  {fetchingFreed ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                      Fetching from Freed.ai...
                    </>
                  ) : (
                    <>
                      <Download className="w-4 h-4 mr-2" />
                      Pull from Freed.ai
                    </>
                  )}
                </Button>
                <Button
                  onClick={handleFetchFromOsmind}
                  disabled={fetchingOsmind}
                  className="bg-gradient-to-r from-pink-600 to-rose-600 hover:from-pink-700 hover:to-rose-700"
                >
                  {fetchingOsmind ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                      Fetching from Osmind...
                    </>
                  ) : (
                    <>
                      <Download className="w-4 h-4 mr-2" />
                      Verify Osmind Data
                    </>
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Quick Actions */}
          <Card>
            <CardHeader>
              <CardTitle>Quick Actions</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-4">
                <Button variant="outline" onClick={() => (window.location.href = '/notes')}>
                  View All Notes
                </Button>
                <Button
                  variant="outline"
                  onClick={() => (window.location.href = '/comparison')}
                >
                  View Comparison
                </Button>
                <Button onClick={() => (window.location.href = '/process')}>
                  Process New Note
                </Button>
              </div>
            </CardContent>
          </Card>
          </>
        )}
      </div>

      {/* Voice Assistant Modal - Placeholder */}
      {isModalOpen && (
        <div
          className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center"
          onClick={() => {
            setIsModalOpen(false);
            setIsVoiceActive(false);
          }}
        >
          <Card className="w-[90%] max-w-2xl max-h-[85vh] overflow-y-auto">
            <CardHeader>
              <CardTitle className="text-2xl bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent">
                Voice Assistant
              </CardTitle>
              <p className="text-muted-foreground">
                Talk to your AI assistant to search patients, check stats, and manage data
              </p>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex justify-center">
                <Button
                  size="lg"
                  variant={isVoiceActive ? 'destructive' : 'default'}
                  onClick={(e) => {
                    e.stopPropagation();
                    setIsVoiceActive(!isVoiceActive);
                  }}
                  className="rounded-full w-20 h-20"
                >
                  <Mic className="w-8 h-8" />
                </Button>
              </div>
              {isVoiceActive && (
                <Card className="bg-purple-50 dark:bg-purple-950/30">
                  <CardContent className="pt-6">
                    <p className="font-semibold text-center mb-4">Try saying:</p>
                    <ul className="space-y-2 text-sm text-muted-foreground">
                      <li>&quot;Search for patients named John&quot;</li>
                      <li>&quot;What are the statistics?&quot;</li>
                      <li>&quot;What notes need to be done?&quot;</li>
                      <li>&quot;Fetch notes from last 10 days&quot;</li>
                      <li>&quot;Add urgent tag to Danny Handley&quot;</li>
                    </ul>
                  </CardContent>
                </Card>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
