import { CheckCircle2, Circle, Hash, MessageSquare, User } from 'lucide-react';
import { useMemo } from 'react';

import { Card, CardContent } from '@/components/ui/card';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { useResolveVoiceEntry } from '@/hooks/useResolveVoiceEntry';
import { cn } from '@/lib/utils';
import { useVoiceCasting } from '@/stores/appStore';
import { calculateVoiceUsage } from '@/utils/voiceUsageHelper';

import { VoiceCard } from './VoiceCard';

interface CharacterData {
  name: string;
  displayName: string;
  lineCount: number;
  totalCharacters: number;
  longestDialogue: number;
  isNarrator: boolean;
  castingNotes?: string;
  role?: string;
  assignedVoice: {
    provider: string;
    voiceName: string;
    voiceId: string;
  } | null;
}

interface CharacterCardProps {
  character: CharacterData;
  onAssignVoice: () => void;
}

export function CharacterCard({
  character,
  onAssignVoice,
}: CharacterCardProps) {
  // All hooks must be called at the top level
  const { getActiveSession, removeVoiceFromAssignment } = useVoiceCasting();
  const activeSession = getActiveSession();

  // Safely access session data with fallbacks
  const screenplayData = activeSession?.screenplayData;

  // Memoize assignments to prevent dependency issues
  const assignments = useMemo(
    () => activeSession?.assignments || new Map(),
    [activeSession?.assignments]
  );
  const assignment = assignments.get(character.name);

  // Resolve voice entry if we have an assignment but no voiceEntry
  const resolvedVoice = useResolveVoiceEntry(
    assignment?.provider,
    assignment?.sts_id
  );

  // Calculate assignment status - memoized for performance
  const assignmentData = useMemo(() => {
    if (!activeSession) {
      return { isAssigned: false, assignment: null };
    }

    const isAssigned = !!(
      assignment &&
      (assignment.sts_id || assignment.provider)
    );

    return { isAssigned, assignment };
  }, [activeSession, assignment]);

  // Calculate voice usage map
  const voiceUsageMap = useMemo(() => {
    if (!activeSession) return new Map();
    return calculateVoiceUsage(
      assignments,
      screenplayData?.characters,
      character.name
    );
  }, [activeSession, assignments, screenplayData?.characters, character.name]);

  // Guard against no active session AFTER all hooks
  if (!activeSession) {
    return (
      <Card className="col-span-1">
        <CardContent className="p-4">
          <p className="text-muted-foreground text-sm">No active session</p>
        </CardContent>
      </Card>
    );
  }

  const { isAssigned } = assignmentData;

  // Use assignment.voiceEntry first, fall back to resolved
  const voiceEntry = assignment?.voiceEntry || resolvedVoice;

  const handleRemoveAssignment = () => {
    removeVoiceFromAssignment(character.name);
  };

  return (
    <TooltipProvider>
      <Card
        className={cn(
          'relative h-full transition-all hover:shadow-md',
          isAssigned && 'border-green-500/30'
        )}
      >
        {/* Assignment Status Indicator */}
        <div className="absolute top-3 right-3 z-10">
          {isAssigned ? (
            <Tooltip>
              <TooltipTrigger asChild>
                <CheckCircle2 className="h-4 w-4 text-green-500" />
              </TooltipTrigger>
              <TooltipContent>
                <p>Assigned</p>
              </TooltipContent>
            </Tooltip>
          ) : (
            <Tooltip>
              <TooltipTrigger asChild>
                <Circle className="text-muted-foreground h-4 w-4" />
              </TooltipTrigger>
              <TooltipContent>
                <p>Unassigned</p>
              </TooltipContent>
            </Tooltip>
          )}
        </div>

        <CardContent className="flex h-full flex-col px-4 py-3">
          {/* Header */}
          <div className="mb-3 flex items-start justify-between">
            <div className="flex min-w-0 flex-1 items-center gap-3">
              <Tooltip>
                <TooltipTrigger asChild>
                  <div
                    className={cn(
                      'shrink-0 rounded-full p-2',
                      character.isNarrator ? 'bg-primary/10' : 'bg-muted'
                    )}
                  >
                    <User className="h-4 w-4" />
                  </div>
                </TooltipTrigger>
                <TooltipContent>
                  <p>{character.isNarrator ? 'Narrator' : 'Character'}</p>
                </TooltipContent>
              </Tooltip>
              <div className="min-w-0 flex-1">
                <h3 className="truncate text-base font-semibold">
                  {character.displayName}
                </h3>
                <div className="text-muted-foreground flex items-center gap-3 text-xs">
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <div className="flex items-center gap-1">
                        <MessageSquare className="h-3 w-3" />
                        <span>{character.lineCount}</span>
                      </div>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>Total lines</p>
                    </TooltipContent>
                  </Tooltip>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <div className="flex items-center gap-1">
                        <Hash className="h-3 w-3" />
                        <span>
                          {character.totalCharacters.toLocaleString()}
                        </span>
                      </div>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>Total characters</p>
                    </TooltipContent>
                  </Tooltip>
                </div>
              </div>
            </div>
          </div>

          {/* Character Notes/Role - This will grow to fill available space */}
          <div className="flex-grow">
            {(character.role || character.castingNotes) && (
              <div className="bg-muted/50 space-y-1 rounded-md p-2">
                {character.role && (
                  <p className="text-xs">
                    <span className="text-muted-foreground">Role:</span>{' '}
                    <span className="font-medium">{character.role}</span>
                  </p>
                )}
                {character.castingNotes && (
                  <p className="text-muted-foreground text-xs">
                    {character.castingNotes}
                  </p>
                )}
              </div>
            )}
          </div>

          {/* Voice Card - Always at the bottom */}
          <div className="mt-3">
            <VoiceCard
              provider={assignment?.provider || 'openai'}
              voiceEntry={voiceEntry || undefined}
              sts_id={assignment?.sts_id}
              isCustom={
                !!(assignment && assignment.provider && !assignment?.sts_id)
              }
              onAssignVoice={onAssignVoice}
              onRemoveAssignment={
                isAssigned ? handleRemoveAssignment : undefined
              }
              showRemoveButton={isAssigned}
              voiceUsageMap={voiceUsageMap}
              currentCharacter={character.name}
            />
          </div>
        </CardContent>
      </Card>
    </TooltipProvider>
  );
}
