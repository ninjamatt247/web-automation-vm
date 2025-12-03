'use client';

import '@/lib/mui-license';

import {
  DataGridPremium,
  GridActionsCellItem,
  GridColDef,
} from '@mui/x-data-grid-premium';
import axios from 'axios';
import { Check, Download, MoreVertical, Search, TrendingDown, TrendingUp, X } from 'lucide-react';
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
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedNote, setSelectedNote] = useState<Note | null>(null);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [datePreset, setDatePreset] = useState('all');
  const [patientSearch, setPatientSearch] = useState('');
  const [syncingFreed, setSyncingFreed] = useState(false);
  const [syncMessage, setSyncMessage] = useState<SyncMessage | null>(null);
  const [noteLimit, setNoteLimit] = useState('1000');

  useEffect(() => {
    fetchNotes();
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

  const filteredNotes = notes.filter((note) => {
    if (patientSearch) {
      const searchLower = patientSearch.toLowerCase();
      const patientNameMatch = note.patient_name
        ?.toLowerCase()
        .includes(searchLower);
      if (!patientNameMatch) return false;
    }

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
    const totalNotes = filteredNotes.length;
    const syncedCount = filteredNotes.filter((n) => n.synced).length;
    const unsyncedCount = totalNotes - syncedCount;

    const noteLengths = filteredNotes
      .map((n) => n.note_length || 0)
      .filter((len) => len > 0);
    const avgLength =
      noteLengths.length > 0
        ? Math.round(
            noteLengths.reduce((sum, len) => sum + len, 0) / noteLengths.length,
          )
        : 0;

    const uniquePatients = new Set(
      filteredNotes.map((n) => n.patient_name).filter(Boolean),
    ).size;

    const sentToAI = filteredNotes.filter((n) => n.sent_to_ai_date).length;
    const pendingAI = totalNotes - sentToAI;

    return {
      totalNotes,
      syncedCount,
      unsyncedCount,
      avgLength,
      uniquePatients,
      sentToAI,
      pendingAI,
      syncRate: totalNotes > 0 ? ((syncedCount / totalNotes) * 100).toFixed(1) : '0',
    };
  }, [filteredNotes]);

  const parseTags = (tags?: string | string[]) => {
    if (!tags) return [];
    try {
      const tagArray = typeof tags === 'string' ? JSON.parse(tags) : tags;
      return Array.isArray(tagArray) ? tagArray : [];
    } catch {
      return [];
    }
  };

  const columns: GridColDef<Note>[] = useMemo(
    () => [
      {
        field: 'patient_name',
        headerName: 'Patient Name',
        width: 150,
        valueGetter: (_value: unknown, row: Note) => row.patient_name || '-',
      },
      {
        field: 'visit_date',
        headerName: 'Visit Date',
        width: 120,
        valueGetter: (_value: unknown, row: Note) =>
          formatVisitDate(row.visit_date),
      },
      {
        field: 'description',
        headerName: 'Description',
        width: 300,
        valueGetter: (_value: unknown, row: Note) =>
          row.description || 'No description',
      },
      {
        field: 'synced',
        headerName: 'Synced',
        width: 100,
        renderCell: (params: { row: Note }) => {
          return params.row.synced ? (
            <Check className="h-5 w-5 text-green-500" />
          ) : (
            <X className="h-5 w-5 text-red-500" />
          );
        },
      },
      {
        field: 'tags',
        headerName: 'Tags',
        width: 200,
        renderCell: (params: { row: Note }) => {
          const tags = parseTags(params.row.tags);
          if (tags.length === 0) return '-';
          return (
            <div className="flex flex-wrap gap-1">
              {tags.slice(0, 2).map((tag: string, idx: number) => (
                <Badge key={idx} variant="secondary">
                  {tag}
                </Badge>
              ))}
              {tags.length > 2 && (
                <Badge variant="outline">+{tags.length - 2}</Badge>
              )}
            </div>
          );
        },
      },
      {
        field: 'note_length',
        headerName: 'Length',
        width: 120,
        valueGetter: (_value: unknown, row: Note) =>
          row.note_length ? row.note_length.toLocaleString() : '-',
      },
      {
        field: 'created_at',
        headerName: 'Created',
        width: 120,
        valueGetter: (_value: unknown, row: Note) =>
          row.created_at ? formatVisitDate(row.created_at) : '-',
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
            <h2 className="text-2xl font-bold tracking-tight">Summary Metrics</h2>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              <Card className="@container/card">
                <CardHeader>
                  <CardDescription>Total Notes</CardDescription>
                  <CardTitle className="text-2xl font-semibold tabular-nums @[250px]/card:text-3xl">
                    {kpiMetrics.totalNotes.toLocaleString()}
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
                    Source clinical documentation
                  </div>
                </CardFooter>
              </Card>

              <Card className="@container/card">
                <CardHeader>
                  <CardDescription>Synced to Osmind</CardDescription>
                  <CardTitle className="text-2xl font-semibold tabular-nums text-green-600 dark:text-green-400 @[250px]/card:text-3xl">
                    {kpiMetrics.syncedCount.toLocaleString()}
                  </CardTitle>
                  <CardAction>
                    <Badge variant="outline" className="text-green-600 dark:text-green-400">
                      <TrendingUp className="h-3 w-3 mr-1" />
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
                  <CardTitle className="text-2xl font-semibold tabular-nums text-orange-600 dark:text-orange-400 @[250px]/card:text-3xl">
                    {kpiMetrics.unsyncedCount.toLocaleString()}
                  </CardTitle>
                  <CardAction>
                    <Badge variant="outline" className="text-orange-600 dark:text-orange-400">
                      <TrendingDown className="h-3 w-3 mr-1" />
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
                  <CardDescription>Avg Note Length</CardDescription>
                  <CardTitle className="text-2xl font-semibold tabular-nums @[250px]/card:text-3xl">
                    {kpiMetrics.avgLength.toLocaleString()}
                  </CardTitle>
                  <CardAction>
                    <Badge variant="outline">
                      Characters
                    </Badge>
                  </CardAction>
                </CardHeader>
                <CardFooter className="flex-col items-start gap-1.5 text-sm">
                  <div className="line-clamp-1 flex gap-2 font-medium">
                    Documentation detail
                  </div>
                  <div className="text-muted-foreground">
                    Average Freed.ai note length
                  </div>
                </CardFooter>
              </Card>
            </div>

            <div className="grid gap-4 md:grid-cols-3">
              <Card className="@container/card">
                <CardHeader>
                  <CardDescription>Unique Patients</CardDescription>
                  <CardTitle className="text-2xl font-semibold tabular-nums @[250px]/card:text-3xl">
                    {kpiMetrics.uniquePatients.toLocaleString()}
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
                    Distinct individuals documented
                  </div>
                </CardFooter>
              </Card>

              <Card className="@container/card">
                <CardHeader>
                  <CardDescription>AI Processed</CardDescription>
                  <CardTitle className="text-2xl font-semibold tabular-nums text-purple-600 dark:text-purple-400 @[250px]/card:text-3xl">
                    {kpiMetrics.sentToAI.toLocaleString()}
                  </CardTitle>
                  <CardAction>
                    <Badge variant="outline" className="text-purple-600 dark:text-purple-400">
                      <TrendingUp className="h-3 w-3 mr-1" />
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
                  <CardDescription>Pending AI Processing</CardDescription>
                  <CardTitle className="text-2xl font-semibold tabular-nums text-yellow-600 dark:text-yellow-400 @[250px]/card:text-3xl">
                    {kpiMetrics.pendingAI.toLocaleString()}
                  </CardTitle>
                  <CardAction>
                    <Badge variant="outline" className="text-yellow-600 dark:text-yellow-400">
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
                    <SelectItem value="0">All Notes</SelectItem>
                  </SelectContent>
                </Select>

                <Button
                  onClick={handleRunFreedSync}
                  disabled={syncingFreed}
                  className="bg-gradient-to-r from-purple-600 to-indigo-600"
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

                {(datePreset === 'custom' || startDate || endDate) && (
                  <>
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
                  </>
                )}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-0">
              <div style={{ width: '100%' }}>
                <DataGridPremium
                  autoHeight
                  rows={filteredNotes}
                  columns={columns}
                  pageSizeOptions={[25, 50, 100, 250, 500, 1000]}
                  initialState={{
                    pagination: {
                      paginationModel: { pageSize: parseInt(noteLimit) || 100, page: 0 },
                    },
                  }}
                  pagination
                  paginationMode="client"
                  disableRowSelectionOnClick
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
                    '& .MuiTablePagination-selectLabel, & .MuiTablePagination-displayedRows': {
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
