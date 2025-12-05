'use client';
import '@/lib/mui-license';

import {
  DataGridPremium,
  GridActionsCellItem,
  GridColDef,
  GridRowSelectionModel,
} from '@mui/x-data-grid-premium';
import axios from 'axios';
import {
  Check,
  Download,
  MoreVertical,
  Search,
  TrendingDown,
  TrendingUp,
  X,
} from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';

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
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
interface Note {
  id: string;
  patient_name?: string;
  visit_date?: string;
  description?: string;
  note_text?: string;
  full_text?: string;
  orig_note?: string;
  original_note?: string;
  synced?: string;
  tags?: string | string[];
  note_length?: number;
  created_at?: string;
  sent_to_ai_date?: string;
}
interface SyncMessage {
  type: 'success' | 'error';
  text: string;
}
export default function NotesPage() {
  const [notes, setNotes] = useState<Note[]>([]);
  const [allNotes, setAllNotes] = useState<Note[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedNote, setSelectedNote] = useState<Note | null>(null);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [datePreset, setDatePreset] = useState('all');
  const [patientSearch, setPatientSearch] = useState('');
  const [includeTags, setIncludeTags] = useState('');
  const [excludeTags, setExcludeTags] = useState('');
  const [syncingFreed, setSyncingFreed] = useState(false);
  const [syncMessage, setSyncMessage] = useState<SyncMessage | null>(null);
  const [noteLimit, setNoteLimit] = useState('1000');
  const [rowSelectionModel, setRowSelectionModel] =
    useState<GridRowSelectionModel>({ type: 'include', ids: new Set() });
  // Handle selection change properly
  const handleSelectionChange = (newSelection: GridRowSelectionModel) => {
    setRowSelectionModel(newSelection);
  };
  const [bulkProcessing, setBulkProcessing] = useState(false);
  const [bulkMessage, setBulkMessage] = useState<SyncMessage | null>(null);
  useEffect(() => {
    fetchNotes();
    fetchAllNotesForMetrics();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [noteLimit]);
  const fetchNotes = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`/api/notes?limit=${noteLimit}`);
      setNotes(response.data.notes || []);
      setError(null);
    } catch (err) {
      setError('Failed to load notes');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };
  const fetchAllNotesForMetrics = async () => {
    try {
      const response = await axios.get(`/api/notes?limit=0`);
      setAllNotes(response.data.notes || []);
    } catch (err) {
      console.error('Failed to load all notes for metrics:', err);
    }
  };
  const getDateRangeForPreset = (preset: string) => {
    const now = new Date();
    const year = now.getFullYear();
    const month = now.getMonth();
    const date = now.getDate();
    const day = now.getDay();
    switch (preset) {
      case 'this_week': {
        const weekStart = new Date(year, month, date - day);
        const weekEnd = new Date(year, month, date - day + 6);
        return { start: weekStart, end: weekEnd };
      }
      case 'last_week': {
        const weekStart = new Date(year, month, date - day - 7);
        const weekEnd = new Date(year, month, date - day - 1);
        return { start: weekStart, end: weekEnd };
      }
      case 'mtd': {
        const monthStart = new Date(year, month, 1);
        return { start: monthStart, end: now };
      }
      case 'last_month': {
        const lastMonthStart = new Date(year, month - 1, 1);
        const lastMonthEnd = new Date(year, month, 0);
        return { start: lastMonthStart, end: lastMonthEnd };
      }
      case 'qtd': {
        const quarter = Math.floor(month / 3);
        const quarterStart = new Date(year, quarter * 3, 1);
        return { start: quarterStart, end: now };
      }
      case 'ytd': {
        const yearStart = new Date(year, 0, 1);
        return { start: yearStart, end: now };
      }
      default:
        return null;
    }
  };
  const handlePresetChange = (preset: string) => {
    setDatePreset(preset);
    if (preset === 'all') {
      setStartDate('');
      setEndDate('');
    } else if (preset === 'custom') {
      // Keep current dates
    } else {
      const range = getDateRangeForPreset(preset);
      if (range) {
        setStartDate(range.start.toISOString().split('T')[0]);
        setEndDate(range.end.toISOString().split('T')[0]);
      }
    }
  };
  const parseVisitDate = (dateStr?: string) => {
    if (!dateStr) return null;
    const match = dateStr.match(/^(\d{1,2})\/(\d{1,2})\/(\d{2})/);
    if (match) {
      const [, month, day, year] = match;
      const fullYear = parseInt(year) < 50 ? `20${year}` : `19${year}`;
      return new Date(
        `${fullYear}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`,
      );
    }
    const date = new Date(dateStr);
    return isNaN(date.getTime()) ? null : date;
  };
  const handleRunFreedSync = async () => {
    try {
      setSyncingFreed(true);
      setSyncMessage(null);
      const response = await axios.post('/api/fetch-from-freed', { days: 7 });
      setSyncMessage({
        type: 'success',
        text:
          response.data.message || 'Successfully synced notes from Freed.ai',
      });
      setTimeout(() => {
        fetchNotes();
      }, 3000);
    } catch (err) {
      const error = err as { response?: { data?: { detail?: string } } };
      setSyncMessage({
        type: 'error',
        text: error.response?.data?.detail || 'Failed to sync from Freed.ai',
      });
      console.error(err);
    } finally {
      setSyncingFreed(false);
    }
  };
  const handleBulkSendToAI = async () => {
    const selectedIds = Array.from(rowSelectionModel.ids);
    if (selectedIds.length === 0) {
      setBulkMessage({ type: 'error', text: 'No notes selected' });
      return;
    }
    try {
      setBulkProcessing(true);
      setBulkMessage(null);
      const noteIds = selectedIds.map((id) => parseInt(id.toString()));
      const response = await axios.post('/api/notes/bulk-send-ai', {
        note_ids: noteIds,
      });
      setBulkMessage({
        type: 'success',
        text: `Successfully sent ${selectedIds.length} note(s) to OpenAI → Osmind pipeline`,
      });
      setRowSelectionModel({ type: 'include', ids: new Set() });
      setTimeout(() => {
        fetchNotes();
      }, 3000);
    } catch (err) {
      const error = err as { response?: { data?: { detail?: string } } };
      setBulkMessage({
        type: 'error',
        text: error.response?.data?.detail || 'Failed to send notes to AI',
      });
      console.error(err);
    } finally {
      setBulkProcessing(false);
    }
  };
  const handleBulkRefetch = async () => {
    const selectedIds = Array.from(rowSelectionModel.ids);
    if (selectedIds.length === 0) {
      setBulkMessage({ type: 'error', text: 'No notes selected' });
      return;
    }
    try {
      setBulkProcessing(true);
      setBulkMessage(null);
      const noteIds = selectedIds.map((id) => parseInt(id.toString()));
      const response = await axios.post('/api/notes/bulk-refetch', {
        note_ids: noteIds,
      });
      setBulkMessage({
        type: 'success',
        text: `Successfully refetched ${selectedIds.length} note(s) from Freed.ai`,
      });
      setRowSelectionModel({ type: 'include', ids: new Set() });
      setTimeout(() => {
        fetchNotes();
      }, 3000);
    } catch (err) {
      const error = err as { response?: { data?: { detail?: string } } };
      setBulkMessage({
        type: 'error',
        text: error.response?.data?.detail || 'Failed to refetch notes',
      });
      console.error(err);
    } finally {
      setBulkProcessing(false);
    }
  };
  const formatVisitDate = (dateStr?: string) => {
    if (!dateStr) return '-';
    if (dateStr.match(/^\d{1,2}\/\d{1,2}\/\d{2}/)) {
      const datePart = dateStr.split(' ')[0];
      return datePart;
    }
    const date = new Date(dateStr);
    if (!isNaN(date.getTime())) {
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const day = String(date.getDate()).padStart(2, '0');
      const year = String(date.getFullYear()).slice(-2);
      return `${month}/${day}/${year}`;
    }
    return dateStr;
  };
  const parseTags = (tags?: string | string[]) => {
    if (!tags) return [];
    try {
      const tagArray = typeof tags === 'string' ? JSON.parse(tags) : tags;
      return Array.isArray(tagArray) ? tagArray : [];
    } catch {
      return [];
    }
  };
  const filteredNotes = notes.filter((note) => {
    // Patient name filter
    if (patientSearch) {
      const searchLower = patientSearch.toLowerCase();
      const patientNameMatch = note.patient_name
        ?.toLowerCase()
        .includes(searchLower);
      if (!patientNameMatch) return false;
    }
    // Tag filters
    const noteTags = parseTags(note.tags);
    // Include tags filter (must have ALL specified tags)
    if (includeTags) {
      const includeTagsList = includeTags
        .split(',')
        .map((t) => t.trim().toLowerCase())
        .filter((t) => t);
      const hasAllIncludeTags = includeTagsList.every((tag) =>
        noteTags.some((noteTag) => noteTag.toLowerCase().includes(tag)),
      );
      if (!hasAllIncludeTags) return false;
    }
    // Exclude tags filter (must NOT have ANY specified tags)
    if (excludeTags) {
      const excludeTagsList = excludeTags
        .split(',')
        .map((t) => t.trim().toLowerCase())
        .filter((t) => t);
      const hasAnyExcludeTag = excludeTagsList.some((tag) =>
        noteTags.some((noteTag) => noteTag.toLowerCase().includes(tag)),
      );
      if (hasAnyExcludeTag) return false;
    }
    // Date filter
    if (!startDate && !endDate) return true;
    const visitDate = parseVisitDate(note.visit_date);
    if (!visitDate) return false;
    const start = startDate ? new Date(startDate) : null;
    const end = endDate ? new Date(endDate) : null;
    if (start && visitDate < start) return false;
    if (end) {
      const endOfDay = new Date(end);
      endOfDay.setHours(23, 59, 59, 999);
      if (visitDate > endOfDay) return false;
    }
    return true;
  });
  // Calculate KPI metrics for filtered notes
  const kpiMetrics = useMemo(() => {
    const totalNotes = allNotes.length;
    const syncedCount = allNotes.filter((n) => n.synced).length;
    const unsyncedCount = totalNotes - syncedCount;
    const noteLengths = allNotes
      .map((n) => n.note_length || 0)
      .filter((len) => len > 0);
    const avgLength =
      noteLengths.length > 0
        ? Math.round(
            noteLengths.reduce((sum, len) => sum + len, 0) / noteLengths.length,
          )
        : 0;
    const uniquePatients = new Set(
      allNotes.map((n) => n.patient_name).filter(Boolean),
    ).size;
    const sentToAI = allNotes.filter((n) => n.sent_to_ai_date).length;
    const pendingAI = totalNotes - sentToAI;
    return {
      totalNotes,
      syncedCount,
      unsyncedCount,
      avgLength,
      uniquePatients,
      sentToAI,
      pendingAI,
      syncRate:
        totalNotes > 0 ? ((syncedCount / totalNotes) * 100).toFixed(1) : '0',
    };
  }, [allNotes]);
  const columns: GridColDef<Note>[] = useMemo(
    () => [
      {
        field: 'patient_name',
        headerName: 'Patient Name',
        width: 150,
        renderCell: (params: { row: Note }) => (
          <div className="flex h-full items-center">
            {params.row.patient_name || '-'}
          </div>
        ),
      },
      {
        field: 'visit_date',
        headerName: 'Visit Date',
        width: 120,
        renderCell: (params: { row: Note }) => (
          <div className="flex h-full items-center">
            {formatVisitDate(params.row.visit_date)}
          </div>
        ),
      },
      {
        field: 'description',
        headerName: 'Description',
        width: 300,
        renderCell: (params: { row: Note }) => (
          <div className="flex h-full items-center">
            {params.row.description || 'No description'}
          </div>
        ),
      },
      {
        field: 'synced',
        headerName: 'Synced',
        width: 100,
        renderCell: (params: { row: Note }) => {
          return (
            <div className="flex h-full items-center justify-center">
              {params.row.synced ? (
                <Check className="h-5 w-5 text-green-500" />
              ) : (
                <X className="h-5 w-5 text-red-500" />
              )}
            </div>
          );
        },
      },
      {
        field: 'sent_to_ai_date',
        headerName: 'Sent to AI',
        width: 150,
        renderCell: (params: { row: Note }) => (
          <div className="flex h-full items-center">
            {params.row.sent_to_ai_date ? formatVisitDate(params.row.sent_to_ai_date) : '-'}
          </div>
        ),
      },
      {
        field: 'tags',
        headerName: 'Tags',
        width: 300,
        renderCell: (params: { row: Note }) => {
          const tags = parseTags(params.row.tags);
          if (tags.length === 0)
            return <span className="text-muted-foreground">-</span>;
          return (
            <div className="flex min-h-[60px] flex-wrap items-center gap-1 py-2">
              {tags.map((tag: string, idx: number) => (
                <Badge
                  key={idx}
                  className="bg-indigo-600 px-2 py-1 text-xs text-white hover:bg-indigo-700"
                >
                  {tag
                    .replace(/_/g, ' ')
                    .replace(/\b\w/g, (l) => l.toUpperCase())}
                </Badge>
              ))}
            </div>
          );
        },
      },
      {
        field: 'actions',
        type: 'actions',
        headerName: 'Actions',
        width: 100,
        getActions: (params: { row: Note }) => [
          <GridActionsCellItem
            key="view"
            icon={<MoreVertical className="h-4 w-4" />}
            label="View"
            onClick={() => setSelectedNote(params.row)}
          />,
        ],
      },
    ],
    [],
  );
  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="flex min-h-[400px] items-center justify-center">
          <div className="border-primary h-12 w-12 animate-spin rounded-full border-b-2"></div>
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
    <div className="container mx-auto space-y-6 px-4 py-8">
      <h1 className="text-4xl font-bold tracking-tight">
        Freed Notes ({filteredNotes.length})
      </h1>
      {notes.length === 0 && !loading ? (
        <Card>
          <CardContent className="space-y-4 pt-6 text-center">
            <p className="text-muted-foreground">No processed notes found.</p>
            <Button onClick={() => (window.location.href = '/process')}>
              Process Your First Note
            </Button>
          </CardContent>
        </Card>
      ) : (
        <>
          {/* KPI Summary Cards */}
          <div className="space-y-4">
            <h2 className="text-2xl font-bold tracking-tight">
              Summary Metrics
            </h2>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              <Card className="@container/card">
                <CardHeader>
                  <CardDescription>Total Notes</CardDescription>
                  <CardTitle className="text-2xl font-semibold tabular-nums @[250px]/card:text-3xl">
                    {kpiMetrics.totalNotes.toLocaleString()}
                  </CardTitle>
                  <CardAction>
                    <Badge variant="outline">
                      <TrendingUp className="mr-1 h-3 w-3" />
                      Active
                    </Badge>
                  </CardAction>
                </CardHeader>
                <CardFooter className="flex-col items-start gap-1.5 text-sm">
                  <div className="line-clamp-1 flex gap-2 font-medium">
                    In Freed.ai system
                  </div>
                  <div className="text-muted-foreground">
                    Source clinical documentation
                  </div>
                </CardFooter>
              </Card>
              <Card className="@container/card">
                <CardHeader>
                  <CardDescription>Synced to Osmind</CardDescription>
                  <CardTitle className="text-2xl font-semibold text-green-600 tabular-nums @[250px]/card:text-3xl dark:text-green-400">
                    {kpiMetrics.syncedCount.toLocaleString()}
                  </CardTitle>
                  <CardAction>
                    <Badge
                      variant="outline"
                      className="text-green-600 dark:text-green-400"
                    >
                      <TrendingUp className="mr-1 h-3 w-3" />
                      {kpiMetrics.syncRate}%
                    </Badge>
                  </CardAction>
                </CardHeader>
                <CardFooter className="flex-col items-start gap-1.5 text-sm">
                  <div className="line-clamp-1 flex gap-2 font-medium">
                    Successfully transferred <TrendingUp className="h-4 w-4" />
                  </div>
                  <div className="text-muted-foreground">
                    Automated EHR integration
                  </div>
                </CardFooter>
              </Card>
              <Card className="@container/card">
                <CardHeader>
                  <CardDescription>Unsynced Notes</CardDescription>
                  <CardTitle className="text-2xl font-semibold text-orange-600 tabular-nums @[250px]/card:text-3xl dark:text-orange-400">
                    {kpiMetrics.unsyncedCount.toLocaleString()}
                  </CardTitle>
                  <CardAction>
                    <Badge
                      variant="outline"
                      className="text-orange-600 dark:text-orange-400"
                    >
                      <TrendingDown className="mr-1 h-3 w-3" />
                      Pending
                    </Badge>
                  </CardAction>
                </CardHeader>
                <CardFooter className="flex-col items-start gap-1.5 text-sm">
                  <div className="line-clamp-1 flex gap-2 font-medium">
                    Need processing
                  </div>
                  <div className="text-muted-foreground">
                    Awaiting AI enhancement and sync
                  </div>
                </CardFooter>
              </Card>
              <Card className="@container/card">
                <CardHeader>
                  <CardDescription>Pending AI Processing</CardDescription>
                  <CardTitle className="text-2xl font-semibold text-yellow-600 tabular-nums @[250px]/card:text-3xl dark:text-yellow-400">
                    {kpiMetrics.pendingAI.toLocaleString()}
                  </CardTitle>
                  <CardAction>
                    <Badge
                      variant="outline"
                      className="text-yellow-600 dark:text-yellow-400"
                    >
                      Queued
                    </Badge>
                  </CardAction>
                </CardHeader>
                <CardFooter className="flex-col items-start gap-1.5 text-sm">
                  <div className="line-clamp-1 flex gap-2 font-medium">
                    Awaiting enhancement
                  </div>
                  <div className="text-muted-foreground">
                    Next in processing pipeline
                  </div>
                </CardFooter>
              </Card>
            </div>
          </div>
          {syncMessage && (
            <div
              className={`flex items-center justify-between rounded-lg p-4 ${
                syncMessage.type === 'success'
                  ? 'bg-green-50 text-green-800 dark:bg-green-950 dark:text-green-200'
                  : 'bg-red-50 text-red-800 dark:bg-red-950 dark:text-red-200'
              }`}
            >
              <span>{syncMessage.text}</span>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setSyncMessage(null)}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          )}
          <Card>
            <CardHeader>
              <CardTitle>Search and Filters</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex flex-wrap gap-4">
                <div className="min-w-[200px] flex-1">
                  <div className="relative">
                    <Search className="text-muted-foreground absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 transform" />
                    <Input
                      placeholder="Search patients..."
                      value={patientSearch}
                      onChange={(e) => setPatientSearch(e.target.value)}
                      className="pl-10"
                    />
                  </div>
                </div>
                <Select value={noteLimit} onValueChange={setNoteLimit}>
                  <SelectTrigger className="w-[150px]">
                    <SelectValue placeholder="Show notes" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="100">Last 100</SelectItem>
                    <SelectItem value="250">Last 250</SelectItem>
                    <SelectItem value="500">Last 500</SelectItem>
                    <SelectItem value="1000">Last 1000</SelectItem>
                    <SelectItem value="2500">Last 2500</SelectItem>
                    <SelectItem value="5000">Last 5000</SelectItem>
                    <SelectItem value="10000">Last 10000</SelectItem>
                    <SelectItem value="0">All Notes</SelectItem>
                  </SelectContent>
                </Select>
                <Button
                  onClick={handleRunFreedSync}
                  disabled={syncingFreed}
                  className="h-9 bg-gradient-to-r from-purple-600 to-indigo-600"
                >
                  {syncingFreed ? (
                    <>
                      <div className="mr-2 h-4 w-4 animate-spin rounded-full border-b-2 border-white" />
                      Syncing...
                    </>
                  ) : (
                    <>
                      <Download className="mr-2 h-4 w-4" />
                      Sync from Freed
                    </>
                  )}
                </Button>
              </div>
              <div className="flex flex-wrap gap-4">
                <Select value={datePreset} onValueChange={handlePresetChange}>
                  <SelectTrigger className="w-[180px]">
                    <SelectValue placeholder="Date preset" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Time</SelectItem>
                    <SelectItem value="this_week">This Week</SelectItem>
                    <SelectItem value="last_week">Last Week</SelectItem>
                    <SelectItem value="mtd">Month to Date</SelectItem>
                    <SelectItem value="last_month">Last Month</SelectItem>
                    <SelectItem value="qtd">Quarter to Date</SelectItem>
                    <SelectItem value="ytd">Year to Date</SelectItem>
                    <SelectItem value="custom">Custom Range</SelectItem>
                  </SelectContent>
                </Select>
                <Input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  placeholder="Start date"
                  className="w-[150px]"
                />
                <Input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  placeholder="End date"
                  className="w-[150px]"
                />
              </div>
              <div className="flex flex-wrap gap-4">
                <Input
                  placeholder="Include tags (comma separated)"
                  value={includeTags}
                  onChange={(e) => setIncludeTags(e.target.value)}
                  className="min-w-[250px] flex-1"
                />
                <Input
                  placeholder="Exclude tags (comma separated)"
                  value={excludeTags}
                  onChange={(e) => setExcludeTags(e.target.value)}
                  className="min-w-[250px] flex-1"
                />
              </div>
            </CardContent>
          </Card>
          {bulkMessage && (
            <div
              className={`flex items-center justify-between rounded-lg p-4 ${
                bulkMessage.type === 'success'
                  ? 'bg-green-50 text-green-800 dark:bg-green-950 dark:text-green-200'
                  : 'bg-red-50 text-red-800 dark:bg-red-950 dark:text-red-200'
              }`}
            >
              <span>{bulkMessage.text}</span>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setBulkMessage(null)}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          )}
          {rowSelectionModel.ids.size > 0 && (
            <Card className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-950/30 dark:to-indigo-950/30">
              <CardContent className="p-4">
                <div className="flex flex-wrap items-center justify-between gap-4">
                  <div className="flex items-center gap-2">
                    <Badge variant="default" className="text-sm">
                      {rowSelectionModel.ids.size} note
                      {rowSelectionModel.ids.size !== 1 ? 's' : ''} selected
                    </Badge>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() =>
                        setRowSelectionModel({
                          type: 'include',
                          ids: new Set(),
                        })
                      }
                    >
                      Clear selection
                    </Button>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Button
                      onClick={handleBulkSendToAI}
                      disabled={bulkProcessing}
                      className="bg-gradient-to-r from-green-600 to-emerald-600"
                    >
                      {bulkProcessing ? (
                        <>
                          <div className="mr-2 h-4 w-4 animate-spin rounded-full border-b-2 border-white" />
                          Processing...
                        </>
                      ) : (
                        <>Send to OpenAI → Osmind</>
                      )}
                    </Button>
                    <Button
                      onClick={handleBulkRefetch}
                      disabled={bulkProcessing}
                      className="bg-gradient-to-r from-purple-600 to-indigo-600"
                    >
                      {bulkProcessing ? (
                        <>
                          <div className="mr-2 h-4 w-4 animate-spin rounded-full border-b-2 border-white" />
                          Refetching...
                        </>
                      ) : (
                        <>
                          <Download className="mr-2 h-4 w-4" />
                          Refetch from Freed
                        </>
                      )}
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
          <Card>
            <CardContent className="p-0">
              <div style={{ width: '100%' }}>
                {filteredNotes.length > 0 && (
                  <DataGridPremium
                    autoHeight
                    rows={filteredNotes}
                    columns={columns}
                    pageSizeOptions={[25, 50, 100, 250, 500, 1000, 5000]}
                    initialState={{
                      pagination: {
                        paginationModel: { pageSize: 25, page: 0 },
                      },
                    }}
                    pagination
                    paginationMode="client"
                    checkboxSelection
                    disableRowSelectionOnClick
                    rowSelectionModel={rowSelectionModel}
                    onRowSelectionModelChange={handleSelectionChange}
                    keepNonExistentRowsSelected
                    getRowHeight={() => 'auto'}
                    isRowSelectable={() => true}
                    sx={{
                      border: 'none',
                      '& .MuiDataGrid-main': {
                        backgroundColor: 'hsl(var(--background))',
                      },
                      '& .MuiDataGrid-cell': {
                        borderColor: 'hsl(var(--border))',
                        color: 'hsl(var(--foreground))',
                      },
                      '& .MuiDataGrid-columnHeaders': {
                        backgroundColor: 'hsl(var(--muted))',
                        borderColor: 'hsl(var(--border))',
                        color: 'hsl(var(--foreground))',
                      },
                      '& .MuiDataGrid-columnHeaderTitle': {
                        color: 'hsl(var(--foreground))',
                        fontWeight: 600,
                      },
                      '& .MuiDataGrid-row': {
                        backgroundColor: 'hsl(var(--background))',
                        '&:hover': {
                          backgroundColor: 'hsl(var(--muted))',
                        },
                        '&.Mui-selected': {
                          backgroundColor: 'hsl(var(--muted))',
                          '&:hover': {
                            backgroundColor: 'hsl(var(--muted))',
                          },
                        },
                      },
                      '& .MuiDataGrid-footerContainer': {
                        borderColor: 'hsl(var(--border))',
                        backgroundColor: 'hsl(var(--background))',
                        color: 'hsl(var(--foreground))',
                      },
                      '& .MuiTablePagination-root': {
                        color: 'hsl(var(--foreground))',
                      },
                      '& .MuiTablePagination-selectLabel, & .MuiTablePagination-displayedRows':
                        {
                          color: 'hsl(var(--foreground))',
                        },
                      '& .MuiSelect-select': {
                        color: 'hsl(var(--foreground))',
                      },
                      '& .MuiSvgIcon-root': {
                        color: 'hsl(var(--foreground))',
                      },
                      '& .MuiDataGrid-overlay': {
                        backgroundColor: 'hsl(var(--background))',
                        color: 'hsl(var(--foreground))',
                      },
                    }}
                  />
                )}
                {filteredNotes.length === 0 && !loading && (
                  <div className="text-muted-foreground flex items-center justify-center p-8">
                    No notes found
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </>
      )}
      <Dialog open={!!selectedNote} onOpenChange={() => setSelectedNote(null)}>
        <DialogContent className="max-h-[80vh] max-w-3xl overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Note Details</DialogTitle>
          </DialogHeader>
          {selectedNote && (
            <div className="space-y-4">
              <div>
                <h3 className="mb-1 font-semibold">Patient</h3>
                <p className="text-muted-foreground">
                  {selectedNote.patient_name || 'N/A'}
                </p>
              </div>
              <div>
                <h3 className="mb-1 font-semibold">Visit Date</h3>
                <p className="text-muted-foreground">
                  {selectedNote.visit_date || 'N/A'}
                </p>
              </div>
              <div>
                <h3 className="mb-1 font-semibold">Description</h3>
                <p className="text-muted-foreground">
                  {selectedNote.description || 'No description'}
                </p>
              </div>
              <div>
                <h3 className="mb-1 font-semibold">Full Note</h3>
                <div className="bg-muted rounded-lg p-4 text-sm whitespace-pre-wrap">
                  {selectedNote.note_text ||
                    selectedNote.full_text ||
                    selectedNote.orig_note ||
                    selectedNote.original_note ||
                    'No note text available'}
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
