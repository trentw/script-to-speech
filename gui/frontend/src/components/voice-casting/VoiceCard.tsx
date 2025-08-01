import {
  AlertTriangle,
  ChevronDown,
  CirclePlus,
  Mic,
  Settings,
  X,
} from 'lucide-react';
import { useState } from 'react';

import { PlayPreviewButton } from '@/components/PlayPreviewButton';
import { Badge } from '@/components/ui/badge';
import { appButtonVariants } from '@/components/ui/button-variants';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import type { VoiceEntry } from '@/types';

import { ProviderAvatar } from './ProviderAvatar';
import { VoiceCardHeader } from './VoiceCardHeader';

interface VoiceCardProps {
  provider: string;
  voiceEntry?: VoiceEntry | undefined;
  sts_id?: string | undefined;
  isCustom?: boolean;
  onAssignVoice: () => void;
  onRemoveAssignment?: (() => void) | undefined;
  showRemoveButton?: boolean;
  showAssignButton?: boolean;
  voiceUsageMap?: Map<string, Array<{ character: string; lineCount: number }>>;
  currentCharacter?: string;
  className?: string;
}

export function VoiceCard({
  provider,
  voiceEntry,
  sts_id,
  isCustom = false,
  onAssignVoice,
  onRemoveAssignment,
  showRemoveButton = false,
  showAssignButton = false,
  voiceUsageMap,
  currentCharacter,
  className,
}: VoiceCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const isAssigned = !!(voiceEntry || sts_id || isCustom);

  // Get voice usage for this voice
  const voiceUsage =
    sts_id && voiceUsageMap ? voiceUsageMap.get(sts_id) || [] : [];

  // Unassigned state
  if (!isAssigned) {
    return (
      <div
        className={cn(
          'border-muted-foreground/25 bg-muted/30 hover:border-muted-foreground/40 hover:bg-muted/50 cursor-pointer rounded-lg border-2 border-dashed p-4 text-center transition-all',
          className
        )}
        onClick={onAssignVoice}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            onAssignVoice();
          }
        }}
        role="button"
        tabIndex={0}
        aria-label="Assign voice to character"
      >
        <div className="text-muted-foreground flex items-center justify-center gap-2 text-sm font-medium">
          <Mic className="h-4 w-4" />
          Assign Voice
        </div>
      </div>
    );
  }

  // Custom voice state
  if (isCustom && !sts_id) {
    return (
      <div
        className={cn(
          'bg-muted/50 rounded-lg border p-3 transition-all hover:shadow-sm',
          className
        )}
      >
        <VoiceCardHeader
          provider={provider}
          title="Custom Voice"
          subtitle="Custom configuration"
          icon={
            <Tooltip>
              <TooltipTrigger asChild>
                <Settings className="text-muted-foreground h-3 w-3" />
              </TooltipTrigger>
              <TooltipContent>
                <p>Custom voice configuration</p>
              </TooltipContent>
            </Tooltip>
          }
          onRemove={onRemoveAssignment}
          showRemoveButton={showRemoveButton}
        />
      </div>
    );
  }

  // Library voice state without full data
  if (!voiceEntry && sts_id) {
    return (
      <div
        className={cn(
          'bg-muted/50 rounded-lg border p-3 transition-all hover:shadow-sm',
          className
        )}
      >
        <VoiceCardHeader
          provider={provider}
          title="Library Voice"
          subtitle={sts_id}
          onRemove={onRemoveAssignment}
          showRemoveButton={showRemoveButton}
        />
      </div>
    );
  }

  // Library voice state with full data
  if (!voiceEntry) return null;

  const voiceName = voiceEntry.description?.provider_name || voiceEntry.sts_id;
  const perceivedAge = voiceEntry.description?.perceived_age;
  const accent = voiceEntry.voice_properties?.accent;
  const tags = voiceEntry.tags?.character_types || [];
  const description = voiceEntry.description?.provider_description;

  const handleCardClick = (e: React.MouseEvent) => {
    // Don't toggle if clicking on interactive elements
    const target = e.target as HTMLElement;
    if (target.closest('button') || target.closest('[role="button"]')) {
      return;
    }
    setIsExpanded(!isExpanded);
  };

  const handleCardKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      setIsExpanded(!isExpanded);
    }
  };

  return (
    <div
      className={cn(
        'bg-muted/50 cursor-pointer rounded-lg border transition-all hover:shadow-sm',
        isExpanded && 'shadow-md',
        className
      )}
      onClick={handleCardClick}
      onKeyDown={handleCardKeyDown}
      role="button"
      tabIndex={0}
      aria-label={`${isExpanded ? 'Collapse' : 'Expand'} voice card details`}
    >
      {/* Main Content */}
      <div className="p-3">
        <div className="flex items-center justify-between">
          <div className="flex min-w-0 flex-1 items-center gap-3">
            {showRemoveButton && onRemoveAssignment && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    className={appButtonVariants({
                      variant: 'list-action',
                      size: 'icon-sm',
                    })}
                    onClick={(e) => {
                      e.stopPropagation();
                      onRemoveAssignment();
                    }}
                  >
                    <X className="h-3 w-3" />
                  </button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>Remove voice assignment</p>
                </TooltipContent>
              </Tooltip>
            )}
            {showAssignButton && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    className={appButtonVariants({
                      variant: 'list-action',
                      size: 'icon-sm',
                    })}
                    onClick={(e) => {
                      e.stopPropagation();
                      onAssignVoice();
                    }}
                  >
                    <CirclePlus className="h-3 w-3" />
                  </button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>Assign voice</p>
                </TooltipContent>
              </Tooltip>
            )}
            <ProviderAvatar provider={provider} size="sm" />
            <div className="min-w-0 flex-1 space-y-1">
              <div className="flex flex-wrap items-center gap-2">
                <p className="truncate text-sm font-medium">{voiceName}</p>
                {perceivedAge && (
                  <Badge variant="outline" className="px-1.5 py-0 text-xs">
                    {perceivedAge.toLowerCase().includes('year')
                      ? perceivedAge
                      : `${perceivedAge} years`}
                  </Badge>
                )}
                {voiceUsage.length > 0 && (
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <div className="flex items-center gap-1 text-xs text-amber-600">
                        <AlertTriangle className="h-3 w-3" />
                        <span>
                          {voiceUsage.length} other assignment
                          {voiceUsage.length > 1 ? 's' : ''}
                        </span>
                      </div>
                    </TooltipTrigger>
                    <TooltipContent className="max-w-sm">
                      <p className="mb-1 font-medium">Also assigned to:</p>
                      <ul className="space-y-0.5 text-xs">
                        {voiceUsage.map(({ character, lineCount }) => (
                          <li key={character}>
                            • {character} ({lineCount} lines)
                          </li>
                        ))}
                      </ul>
                    </TooltipContent>
                  </Tooltip>
                )}
              </div>
              {accent && !isExpanded && (
                <p className="text-muted-foreground truncate text-xs">
                  {accent} accent
                </p>
              )}
            </div>
          </div>

          <div className="flex items-center gap-1">
            {voiceEntry && voiceEntry.preview_url && (
              <PlayPreviewButton
                voice={voiceEntry}
                providerName={provider}
                characterName={currentCharacter}
                tooltip="Play voice preview"
              />
            )}
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  className={cn(
                    appButtonVariants({
                      variant: 'list-action',
                      size: 'icon-sm',
                    }),
                    'transition-transform duration-200',
                    isExpanded && 'rotate-180'
                  )}
                  onClick={(e) => {
                    e.stopPropagation();
                    setIsExpanded(!isExpanded);
                  }}
                >
                  <ChevronDown className="h-3 w-3" />
                </button>
              </TooltipTrigger>
              <TooltipContent>
                <p>{isExpanded ? 'Hide details' : 'Show details'}</p>
              </TooltipContent>
            </Tooltip>
          </div>
        </div>
      </div>

      {/* Expanded Content */}
      <div
        className={cn(
          'overflow-hidden transition-all duration-300 ease-in-out',
          isExpanded ? 'max-h-96' : 'max-h-0'
        )}
      >
        <div className="space-y-2 border-t px-3 pt-2 pb-3">
          {accent && (
            <div className="text-xs">
              <span className="text-muted-foreground">Accent:</span>{' '}
              <span className="font-medium">{accent}</span>
            </div>
          )}
          {tags.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {tags.map((tag) => (
                <Badge key={tag} variant="outline" className="text-xs">
                  {tag}
                </Badge>
              ))}
            </div>
          )}
          {description && (
            <p className="text-muted-foreground text-xs">{description}</p>
          )}
          <div className="text-muted-foreground text-xs">
            ID: {voiceEntry.sts_id}
          </div>
        </div>
      </div>
    </div>
  );
}
