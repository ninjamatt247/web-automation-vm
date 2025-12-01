'use client';

import axios from 'axios';
import { Check, Download, MoreVertical, Search, X } from 'lucide-react';
import { useEffect, useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

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
  const [noteLimit, setNoteLimit] = useState('100');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalNotes, setTotalNotes] = useState(0);

  useEffect(() => {
    fetchNotes();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [noteLimit, currentPage]);

  const fetchNotes = async () => {
    try {
      setLoading(true);
      const offset = (currentPage - 1) * parseInt(noteLimit);
      const response = await axios.get(
        `/api/osmind-notes?limit=${noteLimit}&offset=${offset}`
      );
      setNotes(response.data.notes || []);
      setTotalNotes(response.data.total || 0);
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
      const patientNameMatch = note.patient_name?.toLowerCase().includes(searchLower);
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
        <div className="bg-destructive/10 text-destructive rounded-lg p-4">{error}</div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8 space-y-6">
      <h1 className="text-4xl font-bold tracking-tight">
        Osmind Notes ({filteredNotes.length})
      </h1>

      {notes.length === 0 && !loading ? (
        <Card>
          <CardContent className="pt-6 text-center space-y-4">
            <p className="text-muted-foreground">No Osmind notes found.</p>
            <p className="text-sm text-muted-foreground">
              Run Osmind sync to fetch notes from the EHR system.
            </p>
          </CardContent>
        </Card>
      ) : (
        <>
          {syncMessage && (
            <div
              className={`rounded-lg p-4 flex items-center justify-between ${
                syncMessage.type === 'success'
                  ? 'bg-green-50 dark:bg-green-950 text-green-800 dark:text-green-200'
                  : 'bg-red-50 dark:bg-red-950 text-red-800 dark:text-red-200'
              }`}
            >
              <span>{syncMessage.text}</span>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setSyncMessage(null)}
              >
                <X className="w-4 h-4" />
              </Button>
            </div>
          )}

          <Card>
            <CardHeader>
              <CardTitle>Search and Filters</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex flex-wrap gap-4">
                <div className="flex-1 min-w-[200px]">
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                    <Input
                      placeholder="Search patients..."
                      value={patientSearch}
                      onChange={(e) => setPatientSearch(e.target.value)}
                      className="pl-10"
                    />
                  </div>
                </div>

                <Select
                  value={noteLimit}
                  onValueChange={(value) => {
                    setNoteLimit(value);
                    setCurrentPage(1);
                  }}
                >
                  <SelectTrigger className="w-[150px]">
                    <SelectValue placeholder="Show notes" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="25">25 per page</SelectItem>
                    <SelectItem value="50">50 per page</SelectItem>
                    <SelectItem value="100">100 per page</SelectItem>
                    <SelectItem value="250">250 per page</SelectItem>
                    <SelectItem value="500">500 per page</SelectItem>
                  </SelectContent>
                </Select>

                <Button
                  onClick={handleRunOsmindSync}
                  disabled={syncingOsmind}
                  className="bg-gradient-to-r from-purple-600 to-indigo-600"
                >
                  {syncingOsmind ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />
                      Syncing...
                    </>
                  ) : (
                    <>
                      <Download className="w-4 h-4 mr-2" />
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
              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Patient</TableHead>
                      <TableHead>Visit Date</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Preview</TableHead>
                      <TableHead>Provider</TableHead>
                      <TableHead>Signed</TableHead>
                      <TableHead>Length</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredNotes.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={8} className="text-center text-muted-foreground">
                          No notes match the current filters
                        </TableCell>
                      </TableRow>
                    ) : (
                      filteredNotes.map((note) => (
                        <TableRow key={note.id}>
                          <TableCell className="font-medium">
                            {note.patient_name || '-'}
                          </TableCell>
                          <TableCell>{formatVisitDate(note.visit_date)}</TableCell>
                          <TableCell>
                            {note.note_type ? (
                              <Badge variant="outline">{note.note_type}</Badge>
                            ) : (
                              '-'
                            )}
                          </TableCell>
                          <TableCell className="max-w-md truncate">
                            {note.full_text?.substring(0, 100) || note.note_text?.substring(0, 100) || '-'}
                            {(note.full_text || note.note_text || '').length > 100 && '...'}
                          </TableCell>
                          <TableCell className="text-sm">
                            {note.rendering_provider_name || '-'}
                          </TableCell>
                          <TableCell>
                            {note.is_signed ? (
                              <Check className="w-4 h-4 text-green-600" />
                            ) : (
                              <X className="w-4 h-4 text-red-600" />
                            )}
                          </TableCell>
                          <TableCell>
                            {note.note_length ? note.note_length.toLocaleString() : '-'}
                          </TableCell>
                          <TableCell className="text-right">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => setSelectedNote(note)}
                            >
                              <MoreVertical className="w-4 h-4" />
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </div>

              {/* Pagination Controls */}
              {totalNotes > 0 && (
                <div className="flex items-center justify-between pt-4">
                  <div className="text-sm text-muted-foreground">
                    Showing {(currentPage - 1) * parseInt(noteLimit) + 1} to{' '}
                    {Math.min(currentPage * parseInt(noteLimit), totalNotes)} of{' '}
                    {totalNotes} notes
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => setCurrentPage((prev) => Math.max(1, prev - 1))}
                      disabled={currentPage === 1}
                    >
                      Previous
                    </Button>
                    <div className="text-sm text-muted-foreground">
                      Page {currentPage} of {Math.ceil(totalNotes / parseInt(noteLimit))}
                    </div>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() =>
                        setCurrentPage((prev) =>
                          Math.min(Math.ceil(totalNotes / parseInt(noteLimit)), prev + 1)
                        )
                      }
                      disabled={currentPage >= Math.ceil(totalNotes / parseInt(noteLimit))}
                    >
                      Next
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}

      <Dialog open={!!selectedNote} onOpenChange={() => setSelectedNote(null)}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Note Details</DialogTitle>
          </DialogHeader>
          {selectedNote && (
            <div className="space-y-6">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <h3 className="text-sm font-medium text-muted-foreground">Patient Name</h3>
                  <p className="mt-1">{selectedNote.patient_name || '-'}</p>
                </div>
                <div>
                  <h3 className="text-sm font-medium text-muted-foreground">Visit Date</h3>
                  <p className="mt-1">{formatVisitDate(selectedNote.visit_date)}</p>
                </div>
                <div>
                  <h3 className="text-sm font-medium text-muted-foreground">Note Type</h3>
                  <p className="mt-1">{selectedNote.note_type || '-'}</p>
                </div>
                <div>
                  <h3 className="text-sm font-medium text-muted-foreground">Provider</h3>
                  <p className="mt-1">{selectedNote.rendering_provider_name || '-'}</p>
                </div>
                <div>
                  <h3 className="text-sm font-medium text-muted-foreground">Location</h3>
                  <p className="mt-1">{selectedNote.location_name || '-'}</p>
                </div>
                <div>
                  <h3 className="text-sm font-medium text-muted-foreground">Signed</h3>
                  <p className="mt-1">{selectedNote.is_signed ? 'Yes' : 'No'}</p>
                </div>
                <div>
                  <h3 className="text-sm font-medium text-muted-foreground">Note Length</h3>
                  <p className="mt-1">
                    {selectedNote.note_length ? `${selectedNote.note_length.toLocaleString()} characters` : '-'}
                  </p>
                </div>
                <div>
                  <h3 className="text-sm font-medium text-muted-foreground">Created</h3>
                  <p className="mt-1">
                    {selectedNote.created_at ? new Date(selectedNote.created_at).toLocaleString() : '-'}
                  </p>
                </div>
              </div>

              <div>
                <h3 className="text-sm font-medium text-muted-foreground mb-2">Full Note Text</h3>
                <div className="bg-muted/50 rounded-lg p-4 max-h-96 overflow-y-auto">
                  <pre className="whitespace-pre-wrap text-sm font-mono">
                    {selectedNote.full_text || selectedNote.note_text || 'No note text available'}
                  </pre>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4 pt-4 border-t">
                <div>
                  <h3 className="text-sm font-medium text-muted-foreground">Osmind Note ID</h3>
                  <p className="mt-1 text-xs font-mono">{selectedNote.osmind_note_id || '-'}</p>
                </div>
                <div>
                  <h3 className="text-sm font-medium text-muted-foreground">Sync Source</h3>
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
