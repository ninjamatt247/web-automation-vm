'use client';

import { useEffect, useState } from 'react';

import axios from 'axios';
import {
  ChevronRight,
  Database,
  Download,
  Pencil,
  Plus,
  RefreshCw,
  Search,
  Trash2,
  X,
} from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
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
import { Textarea } from '@/components/ui/textarea';

interface TableInfo {
  name: string;
  row_count: number;
}

interface ColumnInfo {
  cid: number;
  name: string;
  type: string;
  notnull: number;
  dflt_value: string | null;
  pk: number;
}

interface QueryResult {
  columns: string[];
  rows: Record<string, any>[];
  row_count: number;
}

export default function DevToolsPage() {
  const [tables, setTables] = useState<TableInfo[]>([]);
  const [selectedTable, setSelectedTable] = useState<string>('');
  const [tableSchema, setTableSchema] = useState<ColumnInfo[]>([]);
  const [tableData, setTableData] = useState<QueryResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [limit, setLimit] = useState('100');
  const [offset, setOffset] = useState(0);
  const [showSqlDialog, setShowSqlDialog] = useState(false);
  const [sqlQuery, setSqlQuery] = useState('');
  const [sqlResult, setSqlResult] = useState<QueryResult | null>(null);
  const [showEditDialog, setShowEditDialog] = useState(false);
  const [editingRow, setEditingRow] = useState<Record<string, any> | null>(null);
  const [isNewRow, setIsNewRow] = useState(false);

  useEffect(() => {
    fetchTables();
  }, []);

  useEffect(() => {
    if (selectedTable) {
      fetchTableSchema();
      fetchTableData();
    }
  }, [selectedTable, limit, offset]);

  const fetchTables = async () => {
    try {
      setLoading(true);
      const response = await axios.get('/api/dev/db/tables');
      setTables(response.data.tables || []);
      setError(null);
    } catch (err) {
      setError('Failed to load database tables');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const fetchTableSchema = async () => {
    try {
      const response = await axios.get(`/api/dev/db/schema/${selectedTable}`);
      setTableSchema(response.data.schema || []);
    } catch (err) {
      console.error('Failed to load table schema:', err);
    }
  };

  const fetchTableData = async () => {
    try {
      setLoading(true);
      const response = await axios.get(
        `/api/dev/db/data/${selectedTable}?limit=${limit}&offset=${offset}`
      );
      setTableData(response.data);
      setError(null);
    } catch (err) {
      setError('Failed to load table data');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const executeSqlQuery = async () => {
    try {
      setLoading(true);
      const response = await axios.post('/api/dev/db/query', {
        query: sqlQuery,
      });
      setSqlResult(response.data);
      setError(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to execute query');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteRow = async (row: Record<string, any>) => {
    if (!confirm('Are you sure you want to delete this record?')) return;

    try {
      setLoading(true);
      await axios.delete(`/api/dev/db/data/${selectedTable}`, {
        data: { row },
      });
      fetchTableData();
      setError(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete record');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveRow = async () => {
    if (!editingRow) return;

    try {
      setLoading(true);
      if (isNewRow) {
        await axios.post(`/api/dev/db/data/${selectedTable}`, editingRow);
      } else {
        await axios.put(`/api/dev/db/data/${selectedTable}`, editingRow);
      }
      fetchTableData();
      setShowEditDialog(false);
      setEditingRow(null);
      setIsNewRow(false);
      setError(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save record');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleAddNew = () => {
    const newRow: Record<string, any> = {};
    tableSchema.forEach((col) => {
      newRow[col.name] = '';
    });
    setEditingRow(newRow);
    setIsNewRow(true);
    setShowEditDialog(true);
  };

  const handleEditRow = (row: Record<string, any>) => {
    setEditingRow({ ...row });
    setIsNewRow(false);
    setShowEditDialog(true);
  };

  const exportTableData = () => {
    if (!tableData || !tableData.rows.length) return;

    const csv = [
      tableData.columns.join(','),
      ...tableData.rows.map((row) =>
        tableData.columns.map((col) => JSON.stringify(row[col] || '')).join(',')
      ),
    ].join('\n');

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${selectedTable}_export.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  return (
    <div className="container mx-auto px-4 py-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold tracking-tight flex items-center gap-2">
            <Database className="w-8 h-8" />
            SQLite Database Manager
          </h1>
          <Badge variant="destructive" className="mt-2">
            Development Only
          </Badge>
        </div>
        <Button onClick={fetchTables} variant="outline">
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh
        </Button>
      </div>

      {error && (
        <div className="bg-destructive/10 text-destructive rounded-lg p-4 flex items-center justify-between">
          <span>{error}</span>
          <Button variant="ghost" size="sm" onClick={() => setError(null)}>
            <X className="w-4 h-4" />
          </Button>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Tables List */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle>Tables ({tables.length})</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {tables.map((table) => (
              <Button
                key={table.name}
                variant={selectedTable === table.name ? 'default' : 'outline'}
                className="w-full justify-start"
                onClick={() => {
                  setSelectedTable(table.name);
                  setOffset(0);
                }}
              >
                <ChevronRight className="w-4 h-4 mr-2" />
                <span className="truncate">{table.name}</span>
                <Badge variant="secondary" className="ml-auto">
                  {table.row_count}
                </Badge>
              </Button>
            ))}
          </CardContent>
        </Card>

        {/* Table Data */}
        <div className="lg:col-span-3 space-y-4">
          {selectedTable ? (
            <>
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center justify-between">
                    <span>{selectedTable}</span>
                    <div className="flex gap-2">
                      <Button size="sm" onClick={handleAddNew}>
                        <Plus className="w-4 h-4 mr-2" />
                        Add Record
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={exportTableData}
                        disabled={!tableData?.rows.length}
                      >
                        <Download className="w-4 h-4 mr-2" />
                        Export CSV
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => setShowSqlDialog(true)}
                      >
                        SQL Query
                      </Button>
                    </div>
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {/* Schema Info */}
                  <div className="bg-muted/50 rounded-lg p-4">
                    <h3 className="font-semibold mb-2">Schema</h3>
                    <div className="flex flex-wrap gap-2">
                      {tableSchema.map((col) => (
                        <Badge
                          key={col.name}
                          variant={col.pk ? 'default' : 'outline'}
                        >
                          {col.name}
                          <span className="ml-1 text-xs opacity-70">
                            {col.type}
                          </span>
                          {col.pk && <span className="ml-1">🔑</span>}
                        </Badge>
                      ))}
                    </div>
                  </div>

                  {/* Search and Pagination */}
                  <div className="flex gap-4 items-center">
                    <div className="flex-1 relative">
                      <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                      <Input
                        placeholder="Search..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="pl-10"
                      />
                    </div>
                    <Select value={limit} onValueChange={setLimit}>
                      <SelectTrigger className="w-[120px]">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="10">10 rows</SelectItem>
                        <SelectItem value="50">50 rows</SelectItem>
                        <SelectItem value="100">100 rows</SelectItem>
                        <SelectItem value="500">500 rows</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  {/* Data Table */}
                  {loading ? (
                    <div className="flex items-center justify-center py-8">
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
                    </div>
                  ) : tableData && tableData.rows.length > 0 ? (
                    <>
                      <div className="rounded-md border overflow-x-auto">
                        <Table>
                          <TableHeader>
                            <TableRow>
                              {tableData.columns.map((col) => (
                                <TableHead key={col}>{col}</TableHead>
                              ))}
                              <TableHead className="text-right">Actions</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {tableData.rows
                              .filter((row) => {
                                if (!searchQuery) return true;
                                return Object.values(row).some((val) =>
                                  String(val)
                                    .toLowerCase()
                                    .includes(searchQuery.toLowerCase())
                                );
                              })
                              .map((row, idx) => (
                                <TableRow key={idx}>
                                  {tableData.columns.map((col) => (
                                    <TableCell
                                      key={col}
                                      className="max-w-xs truncate"
                                    >
                                      {row[col] !== null &&
                                      row[col] !== undefined
                                        ? String(row[col])
                                        : '-'}
                                    </TableCell>
                                  ))}
                                  <TableCell className="text-right">
                                    <div className="flex gap-2 justify-end">
                                      <Button
                                        size="sm"
                                        variant="ghost"
                                        onClick={() => handleEditRow(row)}
                                      >
                                        <Pencil className="w-4 h-4" />
                                      </Button>
                                      <Button
                                        size="sm"
                                        variant="ghost"
                                        onClick={() => handleDeleteRow(row)}
                                      >
                                        <Trash2 className="w-4 h-4 text-destructive" />
                                      </Button>
                                    </div>
                                  </TableCell>
                                </TableRow>
                              ))}
                          </TableBody>
                        </Table>
                      </div>

                      {/* Pagination */}
                      <div className="flex items-center justify-between">
                        <div className="text-sm text-muted-foreground">
                          Showing {offset + 1} to{' '}
                          {Math.min(
                            offset + parseInt(limit),
                            tableData.row_count
                          )}{' '}
                          of {tableData.row_count} records
                        </div>
                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => setOffset(Math.max(0, offset - parseInt(limit)))}
                            disabled={offset === 0}
                          >
                            Previous
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => setOffset(offset + parseInt(limit))}
                            disabled={
                              offset + parseInt(limit) >= tableData.row_count
                            }
                          >
                            Next
                          </Button>
                        </div>
                      </div>
                    </>
                  ) : (
                    <div className="text-center py-8 text-muted-foreground">
                      No data found
                    </div>
                  )}
                </CardContent>
              </Card>
            </>
          ) : (
            <Card>
              <CardContent className="py-12 text-center text-muted-foreground">
                <Database className="w-16 h-16 mx-auto mb-4 opacity-50" />
                <p>Select a table to view and manage data</p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      {/* SQL Query Dialog */}
      <Dialog open={showSqlDialog} onOpenChange={setShowSqlDialog}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Execute SQL Query</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>SQL Query</Label>
              <Textarea
                value={sqlQuery}
                onChange={(e) => setSqlQuery(e.target.value)}
                placeholder="SELECT * FROM table_name WHERE ..."
                className="font-mono h-32"
              />
            </div>
            <Button onClick={executeSqlQuery} disabled={!sqlQuery}>
              Execute Query
            </Button>

            {sqlResult && (
              <div className="space-y-2">
                <h3 className="font-semibold">
                  Results ({sqlResult.row_count} rows)
                </h3>
                <div className="rounded-md border overflow-x-auto max-h-96">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        {sqlResult.columns.map((col) => (
                          <TableHead key={col}>{col}</TableHead>
                        ))}
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {sqlResult.rows.map((row, idx) => (
                        <TableRow key={idx}>
                          {sqlResult.columns.map((col) => (
                            <TableCell key={col} className="max-w-xs truncate">
                              {row[col] !== null && row[col] !== undefined
                                ? String(row[col])
                                : '-'}
                            </TableCell>
                          ))}
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Edit/Add Dialog */}
      <Dialog open={showEditDialog} onOpenChange={setShowEditDialog}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {isNewRow ? 'Add New Record' : 'Edit Record'}
            </DialogTitle>
          </DialogHeader>
          {editingRow && (
            <div className="space-y-4">
              {tableSchema.map((col) => (
                <div key={col.name}>
                  <Label>
                    {col.name}
                    {col.pk && <span className="ml-1 text-xs">(Primary Key)</span>}
                    {col.notnull === 1 && (
                      <span className="ml-1 text-xs text-destructive">*</span>
                    )}
                  </Label>
                  <Input
                    value={editingRow[col.name] || ''}
                    onChange={(e) =>
                      setEditingRow({
                        ...editingRow,
                        [col.name]: e.target.value,
                      })
                    }
                    placeholder={col.type}
                    disabled={col.pk && !isNewRow}
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Type: {col.type}
                    {col.dflt_value && ` | Default: ${col.dflt_value}`}
                  </p>
                </div>
              ))}
            </div>
          )}
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setShowEditDialog(false);
                setEditingRow(null);
                setIsNewRow(false);
              }}
            >
              Cancel
            </Button>
            <Button onClick={handleSaveRow} disabled={loading}>
              {loading ? 'Saving...' : 'Save'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
