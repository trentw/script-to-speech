import { useQueryClient } from '@tanstack/react-query';
import { Check, ChevronDown, Edit2, Plus, Trash2, X } from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';
import { Badge } from '@/components/ui/badge';
import { appButtonVariants } from '@/components/ui/button-variants';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { useUpdateCastingInstructions } from '@/hooks/mutations/useUpdateCastingInstructions';
import {
  type CastingInstruction,
  type CastingInstructionsData,
  useCastingInstructions,
} from '@/hooks/queries/useCastingInstructions';
import { cn } from '@/lib/utils';
import type { ProviderInfo } from '@/types';

// ── InstructionRow ───────────────────────────────────────────────────────

interface InstructionRowProps {
  instruction: CastingInstruction;
  onToggle: (id: string) => void;
  onUpdate: (id: string, text: string) => void;
  onDelete: (id: string) => void;
  startInEditMode?: boolean;
}

function InstructionRow({
  instruction,
  onToggle,
  onUpdate,
  onDelete,
  startInEditMode,
}: InstructionRowProps) {
  const [editing, setEditing] = useState(startInEditMode ?? false);
  const [localText, setLocalText] = useState(instruction.text);
  const inputRef = useRef<HTMLInputElement>(null);
  const textRef = useRef<HTMLDivElement>(null);
  const [isOverflowing, setIsOverflowing] = useState(false);

  useEffect(() => {
    if (!editing) setLocalText(instruction.text);
  }, [instruction.text, editing]);

  useEffect(() => {
    if (editing) {
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }, [editing]);

  const checkOverflow = useCallback(() => {
    const el = textRef.current;
    if (el) setIsOverflowing(el.scrollWidth > el.clientWidth);
  }, []);

  useEffect(() => {
    checkOverflow();
    window.addEventListener('resize', checkOverflow);
    return () => window.removeEventListener('resize', checkOverflow);
  }, [checkOverflow, instruction.text]);

  const handleSave = () => {
    const trimmed = localText.trim();
    if (!trimmed) {
      // Empty text on save → delete the instruction
      onDelete(instruction.id);
      return;
    }
    if (trimmed !== instruction.text) {
      onUpdate(instruction.id, trimmed);
    }
    setEditing(false);
  };

  const handleCancel = () => {
    if (!instruction.text) {
      // New row with no prior text → remove it
      onDelete(instruction.id);
      return;
    }
    setLocalText(instruction.text);
    setEditing(false);
  };

  const handleBlur = () => {
    const trimmed = localText.trim();
    if (!trimmed && !instruction.text) {
      onDelete(instruction.id);
      return;
    }
    if (trimmed !== instruction.text) {
      handleSave();
    } else {
      setEditing(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleSave();
    if (e.key === 'Escape') handleCancel();
  };

  if (editing) {
    return (
      <div className="flex items-center gap-2 py-1 pl-6">
        <Input
          ref={inputRef}
          value={localText}
          onChange={(e) => setLocalText(e.target.value)}
          onKeyDown={handleKeyDown}
          onBlur={handleBlur}
          placeholder="Enter instruction..."
          className="h-8 text-sm"
        />
        <Tooltip>
          <TooltipTrigger asChild>
            <button
              className={`${appButtonVariants({
                variant: 'list-action',
                size: 'icon-sm',
              })} shrink-0 text-green-600 hover:text-green-700`}
              onMouseDown={(e) => e.preventDefault()}
              onClick={handleSave}
            >
              <Check className="h-3.5 w-3.5" />
            </button>
          </TooltipTrigger>
          <TooltipContent>Save</TooltipContent>
        </Tooltip>
        <Tooltip>
          <TooltipTrigger asChild>
            <button
              className={`${appButtonVariants({
                variant: 'list-action',
                size: 'icon-sm',
              })} shrink-0`}
              onMouseDown={(e) => e.preventDefault()}
              onClick={handleCancel}
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </TooltipTrigger>
          <TooltipContent>Cancel</TooltipContent>
        </Tooltip>
      </div>
    );
  }

  const textContent = (
    <div
      ref={textRef}
      className={cn(
        'min-w-0 truncate text-sm',
        !instruction.enabled && 'text-muted-foreground line-through'
      )}
    >
      {instruction.text}
    </div>
  );

  return (
    <div className="flex items-center gap-2 py-1">
      <Checkbox
        checked={instruction.enabled}
        onCheckedChange={() => onToggle(instruction.id)}
        className="shrink-0"
      />
      <div className="min-w-0 flex-1">
        {isOverflowing ? (
          <Tooltip>
            <TooltipTrigger asChild>{textContent}</TooltipTrigger>
            <TooltipContent side="bottom" className="max-w-sm">
              <p className="text-sm whitespace-pre-wrap">{instruction.text}</p>
            </TooltipContent>
          </Tooltip>
        ) : (
          textContent
        )}
      </div>
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            className={`${appButtonVariants({
              variant: 'list-action',
              size: 'icon-sm',
            })} shrink-0`}
            onClick={() => setEditing(true)}
          >
            <Edit2 className="h-3 w-3" />
          </button>
        </TooltipTrigger>
        <TooltipContent>Edit</TooltipContent>
      </Tooltip>
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            className={`${appButtonVariants({
              variant: 'list-action',
              size: 'icon-sm',
            })} shrink-0 text-red-500 hover:text-red-600`}
            onClick={() => onDelete(instruction.id)}
          >
            <Trash2 className="h-3 w-3" />
          </button>
        </TooltipTrigger>
        <TooltipContent>Delete</TooltipContent>
      </Tooltip>
    </div>
  );
}

// ── InstructionSection ───────────────────────────────────────────────────

interface InstructionSectionProps {
  label: string;
  instructions: CastingInstruction[];
  onToggle: (id: string) => void;
  onUpdate: (id: string, text: string) => void;
  onDelete: (id: string) => void;
  onAdd: () => void;
  newRowId: string | null;
}

function InstructionSection({
  label,
  instructions,
  onToggle,
  onUpdate,
  onDelete,
  onAdd,
  newRowId,
}: InstructionSectionProps) {
  return (
    <div className="space-y-1">
      <div className="text-muted-foreground text-xs font-medium">{label}</div>
      {instructions.map((instr) => (
        <InstructionRow
          key={instr.id}
          instruction={instr}
          onToggle={onToggle}
          onUpdate={onUpdate}
          onDelete={onDelete}
          startInEditMode={instr.id === newRowId}
        />
      ))}
      <button
        className={`${appButtonVariants({
          variant: 'secondary',
          size: 'sm',
        })} mt-1 gap-1 text-xs`}
        onClick={onAdd}
      >
        <Plus className="h-3 w-3" />
        Add Instruction
      </button>
    </div>
  );
}

// ── CastingInstructionsCard ──────────────────────────────────────────────

interface CastingInstructionsCardProps {
  selectedProviders: string[];
  providers: ProviderInfo[];
}

export function CastingInstructionsCard({
  selectedProviders,
  providers,
}: CastingInstructionsCardProps) {
  const { data: instructions } = useCastingInstructions();
  const updateMutation = useUpdateCastingInstructions();
  const queryClient = useQueryClient();
  const [collapsed, setCollapsed] = useState(true);
  const [newRowId, setNewRowId] = useState<string | null>(null);

  // Build a working copy of the data (or default empty)
  const current: CastingInstructionsData = instructions ?? {
    overall: [],
    provider_instructions: {},
  };

  // Count active instructions
  const activeCount =
    current.overall.filter((i) => i.enabled).length +
    Object.values(current.provider_instructions).reduce(
      (sum, items) => sum + items.filter((i) => i.enabled).length,
      0
    );

  // Save to server (for real content changes only)
  const save = useCallback(
    (next: CastingInstructionsData) => {
      updateMutation.mutate(next);
    },
    [updateMutation]
  );

  // Update query cache locally without triggering a server call
  const setLocal = useCallback(
    (next: CastingInstructionsData) => {
      queryClient.setQueryData(['casting-instructions'], next);
    },
    [queryClient]
  );

  // ── Unified handler factory ──
  // Both overall and per-provider sections use the same logic;
  // only the data path differs (captured by `buildNext`).

  const makeHandlers = (
    items: CastingInstruction[],
    buildNext: (items: CastingInstruction[]) => CastingInstructionsData
  ) => {
    const toggle = (id: string) => {
      save(
        buildNext(
          items.map((i) => (i.id === id ? { ...i, enabled: !i.enabled } : i))
        )
      );
    };

    const update = (id: string, text: string) => {
      save(buildNext(items.map((i) => (i.id === id ? { ...i, text } : i))));
      setNewRowId(null);
    };

    const del = (id: string) => {
      const filtered = items.filter((i) => i.id !== id);
      const next = buildNext(filtered);
      if (id === newRowId) {
        setLocal(next);
        setNewRowId(null);
      } else {
        save(next);
      }
    };

    const add = () => {
      const id = crypto.randomUUID();
      const next = buildNext([...items, { id, text: '', enabled: true }]);
      setLocal(next);
      setNewRowId(id);
    };

    return { items, toggle, update, del, add };
  };

  // Only show providers that are selected
  const providerList = providers.filter((p) =>
    selectedProviders.includes(p.identifier)
  );

  const overallHandlers = makeHandlers(current.overall, (items) => ({
    ...current,
    overall: items,
  }));

  const overallActiveCount = current.overall.filter((i) => i.enabled).length;

  return (
    <Card>
      <CardHeader
        className="cursor-pointer select-none"
        onClick={() => setCollapsed(!collapsed)}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CardTitle className="text-base">
              Custom Casting Instructions
            </CardTitle>
            {activeCount > 0 && (
              <Badge variant="secondary" className="text-xs">
                {activeCount} active
              </Badge>
            )}
          </div>
          <ChevronDown
            className={cn(
              'text-muted-foreground h-4 w-4 transition-transform duration-200',
              !collapsed && 'rotate-180'
            )}
          />
        </div>
      </CardHeader>

      {!collapsed && (
        <CardContent className="pt-0">
          <Accordion type="multiple" className="w-full">
            {/* Overall instructions */}
            <AccordionItem value="overall">
              <AccordionTrigger className="py-2 text-sm">
                <span className="flex items-center gap-2">
                  Overall
                  {overallActiveCount > 0 && (
                    <Badge variant="secondary" className="text-xs">
                      {overallActiveCount}
                    </Badge>
                  )}
                </span>
              </AccordionTrigger>
              <AccordionContent className="pl-1">
                <InstructionSection
                  label="Overall casting instructions"
                  instructions={overallHandlers.items}
                  onToggle={overallHandlers.toggle}
                  onUpdate={overallHandlers.update}
                  onDelete={overallHandlers.del}
                  onAdd={overallHandlers.add}
                  newRowId={newRowId}
                />
              </AccordionContent>
            </AccordionItem>

            {/* Per-provider instructions */}
            {providerList.map((provider) => {
              const handlers = makeHandlers(
                current.provider_instructions[provider.identifier] || [],
                (items) => {
                  const pi = {
                    ...current.provider_instructions,
                    [provider.identifier]: items,
                  };
                  if (items.length === 0) {
                    delete pi[provider.identifier];
                  }
                  return { ...current, provider_instructions: pi };
                }
              );
              return (
                <AccordionItem
                  key={provider.identifier}
                  value={provider.identifier}
                >
                  <AccordionTrigger className="py-2 text-sm">
                    <span className="flex items-center gap-2">
                      {provider.name || provider.identifier}
                      {handlers.items.filter((i) => i.enabled).length > 0 && (
                        <Badge variant="secondary" className="text-xs">
                          {handlers.items.filter((i) => i.enabled).length}
                        </Badge>
                      )}
                    </span>
                  </AccordionTrigger>
                  <AccordionContent className="pl-1">
                    <InstructionSection
                      label={`${provider.name || provider.identifier} specific casting instructions`}
                      instructions={handlers.items}
                      onToggle={handlers.toggle}
                      onUpdate={handlers.update}
                      onDelete={handlers.del}
                      onAdd={handlers.add}
                      newRowId={newRowId}
                    />
                  </AccordionContent>
                </AccordionItem>
              );
            })}
          </Accordion>
        </CardContent>
      )}
    </Card>
  );
}
