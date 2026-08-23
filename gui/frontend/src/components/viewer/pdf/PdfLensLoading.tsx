import { Loader2 } from 'lucide-react';

/** Suspense fallback while the lazy PDF lens (react-pdf + pdf.js) loads. */
export function PdfLensLoading() {
  return (
    <div className="flex flex-1 items-center justify-center py-16">
      <Loader2 className="text-muted-foreground h-6 w-6 animate-spin" />
      <span className="text-muted-foreground ml-2 text-sm">
        Loading PDF viewer...
      </span>
    </div>
  );
}
