'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export default function ProcessPage() {
  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-4xl font-bold tracking-tight mb-6">Process Note</h1>
      <Card>
        <CardHeader>
          <CardTitle>Process New Note</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">
            This page will allow processing new medical notes. Migration in progress...
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
