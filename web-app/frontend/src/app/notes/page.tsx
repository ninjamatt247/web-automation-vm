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
      return new Date(`${fullYear}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`);
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
        text: response.data.message || 'Successfully synced notes from Freed.ai',
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
      const patientNameMatch = note.patient_name?.toLowerCase().includes(searchLower);
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

  const parseTags = (tags?: string | string[]) => {
    if (!tags) return [];
    try {
      const tagArray = typeof tags === 'string' ? JSON.parse(tags) : tags;
      return Array.isArray(tagArray) ? tagArray : [];
    } catch {
      return [];
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
        <div className="bg-destructive/10 text-destructive rounded-lg p-4">{error}</div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8 space-y-6">
      <h1 className="text-4xl font-bold tracking-tight">
        Freed Notes ({filteredNotes.length})
      </h1>

      {notes.length === 0 && !loading ? (
        <Card>
          <CardContent className="pt-6 text-center space-y-4">
            <p className="text-muted-foreground">No processed notes found.</p>
            <Button onClick={() => (window.location.href = '/process')}>
              Process Your First Note
            </Button>
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
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />
                      Syncing...
                    </>
                  ) : (
                    <>
                      <Download className="w-4 h-4 mr-2" />
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
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Patient Name</TableHead>
                      <TableHead>Visit Date</TableHead>
                      <TableHead>Description</TableHead>
                      <TableHead>Synced</TableHead>
                      <TableHead>Tags</TableHead>
                      <TableHead>Length</TableHead>
                      <TableHead>Created</TableHead>
                      <TableHead>Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredNotes.map((note) => {
                      const tags = parseTags(note.tags);
                      return (
                        <TableRow key={note.id}>
                          <TableCell className="font-medium">
                            {note.patient_name || '-'}
                          </TableCell>
                          <TableCell>{formatVisitDate(note.visit_date)}</TableCell>
                          <TableCell className="max-w-md truncate">
                            {note.description || 'No description'}
                          </TableCell>
                          <TableCell>
                            {note.synced ? (
                              <Check className="w-5 h-5 text-green-500" />
                            ) : (
                              <X className="w-5 h-5 text-red-500" />
                            )}
                          </TableCell>
                          <TableCell>
                            {tags.length > 0 ? (
                              <div className="flex gap-1 flex-wrap">
                                {tags.slice(0, 2).map((tag, idx) => (
                                  <Badge key={idx} variant="secondary">
                                    {tag}
                                  </Badge>
                                ))}
                                {tags.length > 2 && (
                                  <Badge variant="outline">+{tags.length - 2}</Badge>
                                )}
                              </div>
                            ) : (
                              '-'
                            )}
                          </TableCell>
                          <TableCell>
                            {note.note_length
                              ? note.note_length.toLocaleString()
                              : '-'}
                          </TableCell>
                          <TableCell>
                            {note.created_at
                              ? formatVisitDate(note.created_at)
                              : '-'}
                          </TableCell>
                          <TableCell>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => setSelectedNote(note)}
                            >
                              <MoreVertical className="w-4 h-4" />
                            </Button>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </>
      )}

      <Dialog open={!!selectedNote} onOpenChange={() => setSelectedNote(null)}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Note Details</DialogTitle>
          </DialogHeader>
          {selectedNote && (
            <div className="space-y-4">
              <div>
                <h3 className="font-semibold mb-1">Patient</h3>
                <p className="text-muted-foreground">
                  {selectedNote.patient_name || 'N/A'}
                </p>
              </div>
              <div>
                <h3 className="font-semibold mb-1">Visit Date</h3>
                <p className="text-muted-foreground">
                  {selectedNote.visit_date || 'N/A'}
                </p>
              </div>
              <div>
                <h3 className="font-semibold mb-1">Description</h3>
                <p className="text-muted-foreground">
                  {selectedNote.description || 'No description'}
                </p>
              </div>
              <div>
                <h3 className="font-semibold mb-1">Full Note</h3>
                <div className="bg-muted p-4 rounded-lg whitespace-pre-wrap text-sm">
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
