'use client';

import SchemaBuilder from '@/components/SchemaBuilder';

export default function SchemaBuilderPage() {
  const handleSave = (schema: any) => {
    console.log('Schema saved:', schema);
    alert('Schema saved successfully!');
  };

  return (
    <div className="container mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">Schema Builder</h1>
      <SchemaBuilder 
        workspaceId="test-workspace" 
        onSave={handleSave}
      />
    </div>
  );
}
