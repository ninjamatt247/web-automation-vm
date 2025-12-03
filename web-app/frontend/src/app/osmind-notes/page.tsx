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

interface OsmindNote {
  id: string;
  patient_name?: string;
  visit_date?: string;
  note_type?: string;
  full_text?: string;
  note_text?: string;
  rendering_provider_name?: string;
  location_name?: string;
  is_signed?: boolean;
  note_length?: number;
  created_at?: string;
  osmind_note_id?: string;
  osmind_patient_id?: string;
  sync_source?: string;
  last_synced_at?: string;
  first_signed_at?: string;
}

interface SyncMessage {
  type: 'success' | 'error';
  text: string;
}

export default function OsmindNotesPage() {
  const [notes, setNotes] = useState<OsmindNote[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedNote, setSelectedNote] = useState<OsmindNote | null>(null);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [datePreset, setDatePreset] = useState('all');
  const [patientSearch, setPatientSearch] = useState('');
  const [syncingOsmind, setSyncingOsmind] = useState(false);
  const [syncMessage, setSyncMessage] = useState<SyncMessage | null>(null);
  const [noteLimit, setNoteLimit] = useState('0');

  useEffect(() => {
    fetchNotes();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [noteLimit]);

  const fetchNotes = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`/api/osmind-notes?limit=${noteLimit}`);
      setNotes(response.data.notes || []);
      setError(null);
    } catch (err) {
      setError('Failed to load Osmind notes');
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
    const date = new Date(dateStr);
    return isNaN(date.getTime()) ? null : date;
  };

  const handleRunOsmindSync = async () => {
    try {
      setSyncingOsmind(true);
      setSyncMessage(null);
      const response = await axios.post('/api/fetch-from-osmind', { days: 7 });
      setSyncMessage({
        type: 'success',
        text: response.data.message || 'Successfully started Osmind sync',
      });
      setTimeout(() => {
        fetchNotes();
      }, 15000);
    } catch (err) {
      const error = err as { response?: { data?: { detail?: string } } };
      setSyncMessage({
        type: 'error',
        text: error.response?.data?.detail || 'Failed to sync from Osmind',
      });
      console.error(err);
    } finally {
      setSyncingOsmind(false);
    }
  };

  const formatVisitDate = (dateStr?: string) => {
    if (!dateStr) return '-';

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

    const visitDate = parseVisitDate(note.visit_date || note.created_at);
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
    const signedCount = filteredNotes.filter((n) => n.is_signed).length;
    const unsignedCount = totalNotes - signedCount;

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

    const uniqueProviders = new Set(
      filteredNotes.map((n) => n.rendering_provider_name).filter(Boolean),
    ).size;

    const syncedFromFreed = filteredNotes.filter((n) => n.sync_source === 'freed').length;

    return {
      totalNotes,
      signedCount,
      unsignedCount,
      avgLength,
      uniquePatients,
      uniqueProviders,
      syncedFromFreed,
      signRate: totalNotes > 0 ? ((signedCount / totalNotes) * 100).toFixed(1) : '0',
    };
  }, [filteredNotes]);

  const columns: GridColDef<OsmindNote>[] = useMemo(
    () => [
      {
        field: 'patient_name',
        headerName: 'Patient',
        width: 150,
        valueGetter: (_value: unknown, row: OsmindNote) =>
          row.patient_name || '-',
      },
      {
        field: 'visit_date',
        headerName: 'Visit Date',
        width: 120,
        valueGetter: (_value: unknown, row: OsmindNote) =>
          formatVisitDate(row.visit_date),
      },
      {
        field: 'note_type',
        headerName: 'Type',
        width: 120,
        renderCell: (params: { row: OsmindNote }) => {
          return params.row.note_type ? (
            <Badge variant="outline">{params.row.note_type}</Badge>
          ) : (
            '-'
          );
        },
      },
      {
        field: 'preview',
        headerName: 'Preview',
        width: 300,
        valueGetter: (_value: unknown, row: OsmindNote) => {
          const text = row.full_text || row.note_text || '';
          return text.substring(0, 100) + (text.length > 100 ? '...' : '');
        },
      },
      {
        field: 'rendering_provider_name',
        headerName: 'Provider',
        width: 150,
        valueGetter: (_value: unknown, row: OsmindNote) =>
          row.rendering_provider_name || '-',
      },
      {
        field: 'is_signed',
        headerName: 'Signed',
        width: 100,
        renderCell: (params: { row: OsmindNote }) => {
          return params.row.is_signed ? (
            <Check className="h-4 w-4 text-green-600" />
          ) : (
            <X className="h-4 w-4 text-red-600" />
          );
        },
      },
      {
        field: 'note_length',
        headerName: 'Length',
        width: 120,
        valueGetter: (_value: unknown, row: OsmindNote) =>
          row.note_length ? row.note_length.toLocaleString() : '-',
      },
      {
        field: 'actions',
        type: 'actions',
        headerName: 'Actions',
        width: 100,
        getActions: (params: { row: OsmindNote }) => [
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
        Osmind Notes ({filteredNotes.length})
      </h1>

      {notes.length === 0 && !loading ? (
        <Card>
          <CardContent className="space-y-4 pt-6 text-center">
            <p className="text-muted-foreground">No Osmind notes found.</p>
            <p className="text-muted-foreground text-sm">
              Run Osmind sync to fetch notes from the EHR system.
            </p>
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
                    In Osmind EHR
                  </div>
                  <div className="text-muted-foreground">
                    Complete clinical documentation
                  </div>
                </CardFooter>
              </Card>

              <Card className="@container/card">
                <CardHeader>
                  <CardDescription>Signed Notes</CardDescription>
                  <CardTitle className="text-2xl font-semibold tabular-nums text-green-600 dark:text-green-400 @[250px]/card:text-3xl">
                    {kpiMetrics.signedCount.toLocaleString()}
                  </CardTitle>
                  <CardAction>
                    <Badge variant="outline" className="text-green-600 dark:text-green-400">
                      <TrendingUp className="h-3 w-3 mr-1" />
                      {kpiMetrics.signRate}%
                    </Badge>
                  </CardAction>
                </CardHeader>
                <CardFooter className="flex-col items-start gap-1.5 text-sm">
                  <div className="line-clamp-1 flex gap-2 font-medium">
                    Provider-approved <TrendingUp className="h-4 w-4" />
                  </div>
                  <div className="text-muted-foreground">
                    Legally finalized documentation
                  </div>
                </CardFooter>
              </Card>

              <Card className="@container/card">
                <CardHeader>
                  <CardDescription>Unsigned Notes</CardDescription>
                  <CardTitle className="text-2xl font-semibold tabular-nums text-orange-600 dark:text-orange-400 @[250px]/card:text-3xl">
                    {kpiMetrics.unsignedCount.toLocaleString()}
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
                    Awaiting signature
                  </div>
                  <div className="text-muted-foreground">
                    Need provider finalization
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
                    Average note comprehensiveness
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
                    Distinct individuals in system
                  </div>
                </CardFooter>
              </Card>

              <Card className="@container/card">
                <CardHeader>
                  <CardDescription>Providers</CardDescription>
                  <CardTitle className="text-2xl font-semibold tabular-nums @[250px]/card:text-3xl">
                    {kpiMetrics.uniqueProviders.toLocaleString()}
                  </CardTitle>
                  <CardAction>
                    <Badge variant="outline">
                      Active
                    </Badge>
                  </CardAction>
                </CardHeader>
                <CardFooter className="flex-col items-start gap-1.5 text-sm">
                  <div className="line-clamp-1 flex gap-2 font-medium">
                    Rendering providers
                  </div>
                  <div className="text-muted-foreground">
                    Clinical staff documenting care
                  </div>
                </CardFooter>
              </Card>

              <Card className="@container/card">
                <CardHeader>
                  <CardDescription>Synced from Freed</CardDescription>
                  <CardTitle className="text-2xl font-semibold tabular-nums text-blue-600 dark:text-blue-400 @[250px]/card:text-3xl">
                    {kpiMetrics.syncedFromFreed.toLocaleString()}
                  </CardTitle>
                  <CardAction>
                    <Badge variant="outline" className="text-blue-600 dark:text-blue-400">
                      <TrendingUp className="h-3 w-3 mr-1" />
                      Auto
                    </Badge>
                  </CardAction>
                </CardHeader>
                <CardFooter className="flex-col items-start gap-1.5 text-sm">
                  <div className="line-clamp-1 flex gap-2 font-medium">
                    Automated integration
                  </div>
                  <div className="text-muted-foreground">
                    AI-processed and synced
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
                    <SelectItem value="25">25 per page</SelectItem>
                    <SelectItem value="50">50 per page</SelectItem>
                    <SelectItem value="100">100 per page</SelectItem>
                    <SelectItem value="250">250 per page</SelectItem>
                    <SelectItem value="500">500 per page</SelectItem>
                    <SelectItem value="1000">1000 per page</SelectItem>
                    <SelectItem value="0">All Notes</SelectItem>
                  </SelectContent>
                </Select>

                <Button
                  onClick={handleRunOsmindSync}
                  disabled={syncingOsmind}
                  className="bg-gradient-to-r from-purple-600 to-indigo-600"
                >
                  {syncingOsmind ? (
                    <>
                      <div className="mr-2 h-4 w-4 animate-spin rounded-full border-b-2 border-white" />
                      Syncing...
                    </>
                  ) : (
                    <>
                      <Download className="mr-2 h-4 w-4" />
                      Sync from Osmind
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

                {(startDate || endDate || patientSearch) && (
                  <Button
                    variant="outline"
                    onClick={() => {
                      setStartDate('');
                      setEndDate('');
                      setDatePreset('all');
                      setPatientSearch('');
                    }}
                  >
                    Clear Filters
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Notes</CardTitle>
            </CardHeader>
            <CardContent>
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
        <DialogContent className="max-h-[90vh] max-w-4xl overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Note Details</DialogTitle>
          </DialogHeader>
          {selectedNote && (
            <div className="space-y-6">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <h3 className="text-muted-foreground text-sm font-medium">
                    Patient Name
                  </h3>
                  <p className="mt-1">{selectedNote.patient_name || '-'}</p>
                </div>
                <div>
                  <h3 className="text-muted-foreground text-sm font-medium">
                    Visit Date
                  </h3>
                  <p className="mt-1">
                    {formatVisitDate(selectedNote.visit_date)}
                  </p>
                </div>
                <div>
                  <h3 className="text-muted-foreground text-sm font-medium">
                    Note Type
                  </h3>
                  <p className="mt-1">{selectedNote.note_type || '-'}</p>
                </div>
                <div>
                  <h3 className="text-muted-foreground text-sm font-medium">
                    Provider
                  </h3>
                  <p className="mt-1">
                    {selectedNote.rendering_provider_name || '-'}
                  </p>
                </div>
                <div>
                  <h3 className="text-muted-foreground text-sm font-medium">
                    Location
                  </h3>
                  <p className="mt-1">{selectedNote.location_name || '-'}</p>
                </div>
                <div>
                  <h3 className="text-muted-foreground text-sm font-medium">
                    Signed
                  </h3>
                  <p className="mt-1">
                    {selectedNote.is_signed ? 'Yes' : 'No'}
                  </p>
                </div>
                <div>
                  <h3 className="text-muted-foreground text-sm font-medium">
                    Note Length
                  </h3>
                  <p className="mt-1">
                    {selectedNote.note_length
                      ? `${selectedNote.note_length.toLocaleString()} characters`
                      : '-'}
                  </p>
                </div>
                <div>
                  <h3 className="text-muted-foreground text-sm font-medium">
                    Created
                  </h3>
                  <p className="mt-1">
                    {selectedNote.created_at
                      ? new Date(selectedNote.created_at).toLocaleString()
                      : '-'}
                  </p>
                </div>
              </div>

              <div>
                <h3 className="text-muted-foreground mb-2 text-sm font-medium">
                  Full Note Text
                </h3>
                <div className="bg-muted/50 max-h-96 overflow-y-auto rounded-lg p-4">
                  <pre className="font-mono text-sm whitespace-pre-wrap">
                    {selectedNote.full_text ||
                      selectedNote.note_text ||
                      'No note text available'}
                  </pre>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4 border-t pt-4">
                <div>
                  <h3 className="text-muted-foreground text-sm font-medium">
                    Osmind Note ID
                  </h3>
                  <p className="mt-1 font-mono text-xs">
                    {selectedNote.osmind_note_id || '-'}
                  </p>
                </div>
                <div>
                  <h3 className="text-muted-foreground text-sm font-medium">
                    Sync Source
                  </h3>
                  <p className="mt-1">{selectedNote.sync_source || '-'}</p>
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
