import {
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Plus,
  Settings,
  Trash2,
  X,
} from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { Slider } from '@/components/ui/slider';
import { Switch } from '@/components/ui/switch';
import type { DetectedPattern } from '@/types';

interface RemovalSectionProps {
  detectedPatterns: DetectedPattern[];
  selectedPatterns: Set<string>;
  onSelectionChange: (patterns: Set<string>) => void;
  manualEntries: string[];
  onManualEntriesChange: (entries: string[]) => void;
  removeLines: number;
  onRemoveLinesChange: (value: number) => void;
  globalReplace: boolean;
  onGlobalReplaceChange: (value: boolean) => void;
}

/**
 * Section for configuring which patterns to remove during reparsing.
 * Includes detected patterns, manual entries, and advanced settings.
 */
export function RemovalSection({
  detectedPatterns,
  selectedPatterns,
  onSelectionChange,
  manualEntries,
  onManualEntriesChange,
  removeLines,
  onRemoveLinesChange,
  globalReplace,
  onGlobalReplaceChange,
}: RemovalSectionProps) {
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [showBlacklisted, setShowBlacklisted] = useState(false);
  const [newEntry, setNewEntry] = useState('');
  const [showNewEntryInput, setShowNewEntryInput] = useState(false);
  const [expandedPatterns, setExpandedPatterns] = useState<Set<string>>(
    new Set()
  );
  const newEntryInputRef = useRef<HTMLInputElement>(null);

  // Focus the new entry input when it becomes visible
  useEffect(() => {
    if (showNewEntryInput) {
      newEntryInputRef.current?.focus();
    }
  }, [showNewEntryInput]);

  // Split patterns into categories
  const regularPatterns = detectedPatterns.filter((p) => !p.isBlacklisted);
  const blacklistedPatterns = detectedPatterns.filter((p) => p.isBlacklisted);

  const togglePattern = (text: string) => {
    const newSelection = new Set(selectedPatterns);
    if (newSelection.has(text)) {
      newSelection.delete(text);
    } else {
      newSelection.add(text);
    }
    onSelectionChange(newSelection);
  };

  const toggleExpandPattern = (text: string) => {
    const newExpanded = new Set(expandedPatterns);
    if (newExpanded.has(text)) {
      newExpanded.delete(text);
    } else {
      newExpanded.add(text);
    }
    setExpandedPatterns(newExpanded);
  };

  const handleAddEntry = () => {
    const trimmed = newEntry.trim();
    if (trimmed && !manualEntries.includes(trimmed)) {
      onManualEntriesChange([...manualEntries, trimmed]);
      setNewEntry('');
      setShowNewEntryInput(false);
    }
  };

  const handleRemoveEntry = (entry: string) => {
    onManualEntriesChange(manualEntries.filter((e) => e !== entry));
  };

  const handleNewEntryBlur = () => {
    const trimmed = newEntry.trim();
    if (trimmed) {
      handleAddEntry();
    } else {
      setShowNewEntryInput(false);
    }
  };

  // When global replace is enabled, remove_lines should be 0
  useEffect(() => {
    if (globalReplace) {
      onRemoveLinesChange(0);
    }
  }, [globalReplace, onRemoveLinesChange]);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <Trash2 className="h-5 w-5" />
          Patterns to Remove
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {regularPatterns.length === 0 && manualEntries.length === 0 ? (
          <p className="text-muted-foreground text-sm">
            No patterns detected. Run detection or add patterns manually below.
          </p>
        ) : (
          <>
            {/* Detected Patterns List */}
            {regularPatterns.length > 0 && (
              <div className="space-y-2">
                <Label>Detected Patterns</Label>
                <div className="space-y-2">
                  {regularPatterns.map((pattern) => {
                    const hasVariations = pattern.variations.length > 0;
                    const hasExpandableContent =
                      hasVariations || pattern.exampleFullLines.length > 0;

                    // Check if all variations are selected (for group checkbox state)
                    const allVariationsSelected =
                      hasVariations &&
                      pattern.variations.every((v) => selectedPatterns.has(v));
                    const someVariationsSelected =
                      hasVariations &&
                      pattern.variations.some((v) => selectedPatterns.has(v));

                    // Toggle all variations at once
                    const toggleAllVariations = () => {
                      const newSelection = new Set(selectedPatterns);
                      if (allVariationsSelected) {
                        // Deselect all variations
                        pattern.variations.forEach((v) =>
                          newSelection.delete(v)
                        );
                      } else {
                        // Select all variations
                        pattern.variations.forEach((v) => newSelection.add(v));
                      }
                      onSelectionChange(newSelection);
                    };

                    return (
                      <div
                        key={pattern.text}
                        className="space-y-2 rounded-md border p-3"
                      >
                        <div className="flex items-start gap-3">
                          {/* Checkbox: for patterns with variations, controls all; otherwise controls root */}
                          <Checkbox
                            id={`pattern-${pattern.text}`}
                            checked={
                              hasVariations
                                ? allVariationsSelected
                                : selectedPatterns.has(pattern.text)
                            }
                            onCheckedChange={() =>
                              hasVariations
                                ? toggleAllVariations()
                                : togglePattern(pattern.text)
                            }
                            className="mt-0.5"
                            // Show indeterminate state when some but not all variations selected
                            ref={(el) => {
                              if (el && hasVariations) {
                                (el as HTMLButtonElement).dataset.state =
                                  someVariationsSelected &&
                                  !allVariationsSelected
                                    ? 'indeterminate'
                                    : allVariationsSelected
                                      ? 'checked'
                                      : 'unchecked';
                              }
                            }}
                          />
                          <div className="min-w-0 flex-1">
                            <label
                              htmlFor={`pattern-${pattern.text}`}
                              className="flex cursor-pointer items-center gap-2"
                            >
                              <span className="truncate font-mono text-sm">
                                {pattern.text}
                              </span>
                              <Badge
                                variant="secondary"
                                className="shrink-0 text-xs"
                              >
                                {pattern.position}
                              </Badge>
                              <span className="text-muted-foreground shrink-0 text-xs">
                                {Math.round(pattern.occurrencePercentage)}% (
                                {pattern.occurrenceCount} pages)
                              </span>
                            </label>
                          </div>
                          {hasExpandableContent && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => toggleExpandPattern(pattern.text)}
                              className="h-6 shrink-0 px-2"
                            >
                              {expandedPatterns.has(pattern.text) ? (
                                <ChevronUp className="h-4 w-4" />
                              ) : (
                                <ChevronDown className="h-4 w-4" />
                              )}
                            </Button>
                          )}
                        </div>

                        {/* Expanded content: variations and example lines */}
                        {expandedPatterns.has(pattern.text) &&
                          hasExpandableContent && (
                            <div className="ml-7 space-y-3">
                              {/* Variations as individually selectable items */}
                              {hasVariations && (
                                <div className="bg-muted/50 space-y-2 rounded p-2">
                                  <p className="text-muted-foreground text-xs font-medium">
                                    Variations ({pattern.variations.length}):
                                  </p>
                                  <div className="space-y-1.5">
                                    {pattern.variations.map((variation) => (
                                      <div
                                        key={variation}
                                        className="flex items-center gap-2"
                                      >
                                        <Checkbox
                                          id={`variation-${variation}`}
                                          checked={selectedPatterns.has(
                                            variation
                                          )}
                                          onCheckedChange={() =>
                                            togglePattern(variation)
                                          }
                                          className="h-3.5 w-3.5"
                                        />
                                        <label
                                          htmlFor={`variation-${variation}`}
                                          className="cursor-pointer truncate font-mono text-xs"
                                        >
                                          {variation}
                                        </label>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}

                              {/* Example lines */}
                              {pattern.exampleFullLines.length > 0 && (
                                <div className="bg-muted/50 space-y-1 rounded p-2">
                                  <p className="text-muted-foreground text-xs font-medium">
                                    Example lines:
                                  </p>
                                  {pattern.exampleFullLines
                                    .slice(0, 3)
                                    .map((line, i) => (
                                      <code
                                        key={i}
                                        className="text-muted-foreground block truncate font-mono text-xs"
                                      >
                                        {line}
                                      </code>
                                    ))}
                                </div>
                              )}
                            </div>
                          )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Manual Entries */}
            {manualEntries.length > 0 && (
              <div className="space-y-2">
                <Label>Manual Entries</Label>
                <div className="space-y-1">
                  {manualEntries.map((entry) => (
                    <div
                      key={entry}
                      className="bg-muted/50 flex items-center gap-2 rounded-md px-3 py-2"
                    >
                      <span className="flex-1 truncate font-mono text-sm">
                        {entry}
                      </span>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleRemoveEntry(entry)}
                        className="h-6 w-6 shrink-0 p-0"
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}

        <Separator />

        {/* Add Manual Entry */}
        <div className="space-y-2">
          <Label>Add Header/Footer to Remove</Label>
          {showNewEntryInput ? (
            <div className="flex gap-2">
              <Input
                ref={newEntryInputRef}
                value={newEntry}
                onChange={(e) => setNewEntry(e.target.value)}
                onBlur={handleNewEntryBlur}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleAddEntry();
                  if (e.key === 'Escape') {
                    setNewEntry('');
                    setShowNewEntryInput(false);
                  }
                }}
                placeholder="Enter text to remove..."
              />
              <Button
                variant="secondary"
                size="icon"
                onClick={handleAddEntry}
                disabled={!newEntry.trim()}
              >
                <Plus className="h-4 w-4" />
              </Button>
            </div>
          ) : (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowNewEntryInput(true)}
              className="w-full"
            >
              <Plus className="mr-2 h-4 w-4" />
              Add Pattern
            </Button>
          )}
        </div>

        {/* Advanced Settings Toggle */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Settings className="h-4 w-4" />
            <span className="text-sm font-medium">Advanced Settings</span>
          </div>
          <Switch checked={showAdvanced} onCheckedChange={setShowAdvanced} />
        </div>

        {/* Advanced Settings Panel */}
        {showAdvanced && (
          <div className="bg-muted/50 space-y-4 rounded-lg p-4">
            {/* Remove Lines */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <Label htmlFor="remove-lines">Lines to Check for Removal</Label>
                <span className="text-muted-foreground text-sm">
                  {globalReplace ? '0 (global)' : removeLines}
                </span>
              </div>
              <Slider
                id="remove-lines"
                value={[removeLines]}
                onValueChange={([value]) => onRemoveLinesChange(value)}
                min={0}
                max={10}
                step={1}
                disabled={globalReplace}
              />
              <p className="text-muted-foreground text-xs">
                Only remove patterns found in the first/last N lines of each
                page
              </p>
            </div>

            {/* Global Replace */}
            <div className="flex items-center justify-between">
              <div>
                <Label htmlFor="global-replace">Global Replace</Label>
                <p className="text-muted-foreground text-xs">
                  Remove patterns anywhere in the document, not just
                  headers/footers
                </p>
              </div>
              <Switch
                id="global-replace"
                checked={globalReplace}
                onCheckedChange={onGlobalReplaceChange}
              />
            </div>

            {globalReplace && (
              <div className="flex gap-2 rounded-md border border-amber-200 bg-amber-50 p-3 dark:border-amber-900 dark:bg-amber-950/30">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600 dark:text-amber-500" />
                <p className="text-xs text-amber-800 dark:text-amber-300">
                  Global replace will remove the pattern anywhere it appears in
                  the document, including in dialogue. Use with caution.
                </p>
              </div>
            )}

            {/* Blacklisted Patterns */}
            {blacklistedPatterns.length > 0 && (
              <>
                <Separator />
                <div className="space-y-2">
                  <button
                    onClick={() => setShowBlacklisted(!showBlacklisted)}
                    className="flex w-full items-center gap-2 text-sm font-medium"
                  >
                    <AlertTriangle className="h-4 w-4 text-amber-500" />
                    <span>
                      Blacklisted Patterns ({blacklistedPatterns.length})
                    </span>
                    {showBlacklisted ? (
                      <ChevronUp className="ml-auto h-4 w-4" />
                    ) : (
                      <ChevronDown className="ml-auto h-4 w-4" />
                    )}
                  </button>
                  <p className="text-muted-foreground text-xs">
                    These patterns are commonly false positives. Enable with
                    caution.
                  </p>

                  {showBlacklisted && (
                    <div className="space-y-2 pt-2">
                      {blacklistedPatterns.map((pattern) => (
                        <div
                          key={pattern.text}
                          className="flex items-center gap-3 rounded-md border border-dashed border-amber-300 p-3 dark:border-amber-700"
                        >
                          <Checkbox
                            id={`blacklisted-${pattern.text}`}
                            checked={selectedPatterns.has(pattern.text)}
                            onCheckedChange={() => togglePattern(pattern.text)}
                          />
                          <label
                            htmlFor={`blacklisted-${pattern.text}`}
                            className="flex flex-1 cursor-pointer items-center gap-2"
                          >
                            <AlertTriangle className="h-3 w-3 text-amber-500" />
                            <span className="truncate font-mono text-sm">
                              {pattern.text}
                            </span>
                            <Badge
                              variant="outline"
                              className="shrink-0 text-xs"
                            >
                              {pattern.position}
                            </Badge>
                            <span className="text-muted-foreground shrink-0 text-xs">
                              {Math.round(pattern.occurrencePercentage)}%
                            </span>
                          </label>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
