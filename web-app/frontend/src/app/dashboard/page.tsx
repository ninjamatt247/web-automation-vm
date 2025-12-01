'use client';

import axios from 'axios';
import { Download, Mic, RefreshCw } from 'lucide-react';
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

interface Stats {
  total_processed?: number;
  total_in_freed?: number;
  complete_in_osmind?: number;
  missing_from_osmind?: number;
  incomplete_in_osmind?: number;
  to_process?: number;
  comparison_timestamp?: string;
}

interface FetchMessage {
  type: 'success' | 'error';
  text: string;
}

export default function DashboardPage() {
  const [stats, setStats] = useState<Stats | null>(null);
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

  const handleFetchFromFreed = async () => {
    try {
      setFetchingFreed(true);
      setFetchMessage(null);
      const response = await axios.post('/api/fetch-from-freed', { days: 7 });
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
          <Button onClick={fetchStats} className="ml-auto" variant="outline">
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {stats && (
        <>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  Total Processed Notes
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stats.total_processed || 0}</div>
              </CardContent>
            </Card>

            {stats.total_in_freed !== undefined && (
              <Card className="border-green-500/50">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">
                    Notes in Freed.ai
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                    {stats.total_in_freed}
                  </div>
                </CardContent>
              </Card>
            )}

            {stats.complete_in_osmind !== undefined && (
              <Card className="border-green-500/50">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">
                    Complete in Osmind
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                    {stats.complete_in_osmind}
                  </div>
                </CardContent>
              </Card>
            )}

            {stats.missing_from_osmind !== undefined && (
              <Card className="border-red-500/50">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">
                    Missing from Osmind
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-red-600 dark:text-red-400">
                    {stats.missing_from_osmind}
                  </div>
                </CardContent>
              </Card>
            )}

            {stats.incomplete_in_osmind !== undefined && (
              <Card className="border-yellow-500/50">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">
                    Incomplete in Osmind
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-yellow-600 dark:text-yellow-400">
                    {stats.incomplete_in_osmind}
                  </div>
                </CardContent>
              </Card>
            )}

            {stats.to_process !== undefined && (
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">
                    Notes to Process
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{stats.to_process}</div>
                </CardContent>
              </Card>
            )}
          </div>

          {stats.comparison_timestamp && (
            <p className="text-sm text-muted-foreground">
              Last comparison: {new Date(stats.comparison_timestamp).toLocaleString()}
            </p>
          )}

          {/* Voice Assistant Button */}
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
