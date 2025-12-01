'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export default function ComparisonPage() {
  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-4xl font-bold tracking-tight mb-6">Comparison</h1>
      <Card>
        <CardHeader>
          <CardTitle>Notes Comparison View</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">
            This page will compare notes between Freed.ai and Osmind. Migration in progress...
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
