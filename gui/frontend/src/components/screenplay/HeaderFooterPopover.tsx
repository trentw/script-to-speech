import { Link } from '@tanstack/react-router';
import { CheckCircle2, Info, Settings2 } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import type { DetectedPattern } from '@/types';

interface HeaderFooterPopoverProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  autoRemovedPatterns: DetectedPattern[];
  suggestedPatterns: DetectedPattern[];
  onConfigureParsing: () => void;
}

/**
 * Dialog shown after PDF import when headers/footers are detected.
 * Shows patterns that were auto-removed (>=40%) and suggestions (20-40%).
 */
export function HeaderFooterPopover({
  open,
  onOpenChange,
  autoRemovedPatterns,
  suggestedPatterns,
  onConfigureParsing,
}: HeaderFooterPopoverProps) {
  const hasAutoRemoved = autoRemovedPatterns.length > 0;
  const hasSuggested = suggestedPatterns.length > 0;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Info className="h-5 w-5 text-blue-500" />
            Header/Footer Detection Results
          </DialogTitle>
          <DialogDescription>
            We analyzed your screenplay PDF for repeating headers and footers.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Auto-removed patterns section */}
          {hasAutoRemoved && (
            <div className="space-y-2">
              <h4 className="flex items-center gap-2 text-sm font-medium">
                <CheckCircle2 className="h-4 w-4 text-green-500" />
                Automatically Removed ({autoRemovedPatterns.length})
              </h4>
              <p className="text-muted-foreground text-xs">
                These patterns appeared on 40% or more of pages and were
                automatically removed during parsing.
              </p>
              <ul className="space-y-1.5">
                {autoRemovedPatterns.map((pattern, index) => (
                  <li
                    key={index}
                    className="bg-muted/50 flex items-center justify-between rounded-md px-3 py-2 text-sm"
                  >
                    <span className="font-mono text-xs">{pattern.text}</span>
                    <div className="flex items-center gap-2">
                      <Badge variant="secondary" className="text-xs">
                        {pattern.position}
                      </Badge>
                      <span className="text-muted-foreground text-xs">
                        {Math.round(pattern.occurrencePercentage)}%
                      </span>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Suggested patterns section */}
          {hasSuggested && (
            <div className="space-y-2">
              <h4 className="flex items-center gap-2 text-sm font-medium">
                <Info className="h-4 w-4 text-amber-500" />
                Suggested for Review ({suggestedPatterns.length})
              </h4>
              <p className="text-muted-foreground text-xs">
                These patterns appeared on 20-40% of pages. Review them in
                Configure Parsing if you want to remove them.
              </p>
              <ul className="space-y-1.5">
                {suggestedPatterns.map((pattern, index) => (
                  <li
                    key={index}
                    className="flex items-center justify-between rounded-md border border-dashed px-3 py-2 text-sm"
                  >
                    <span className="font-mono text-xs">{pattern.text}</span>
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="text-xs">
                        {pattern.position}
                      </Badge>
                      <span className="text-muted-foreground text-xs">
                        {Math.round(pattern.occurrencePercentage)}%
                      </span>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Notice about reviewing speakers */}
          <div className="bg-muted/30 rounded-md p-3">
            <p className="text-muted-foreground text-xs">
              <strong>Next step:</strong> Review the speakers and chunk types on
              the Screenplay Info tab to verify the parse results look correct.
            </p>
          </div>
        </div>

        <DialogFooter className="flex-col gap-2 sm:flex-row">
          <Button
            variant="outline"
            onClick={onConfigureParsing}
            className="flex items-center gap-2"
          >
            <Settings2 className="h-4 w-4" />
            Configure Parsing
          </Button>
          <Button onClick={() => onOpenChange(false)} asChild>
            <Link to="/project/screenplay">View Screenplay Info</Link>
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
