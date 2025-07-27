import { CheckCircle2, Circle, MessageSquare, Mic, User } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';

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
  const isAssigned = !!character.assignedVoice;

  return (
    <Card
      className={`transition-all ${isAssigned ? 'border-green-500/50' : ''}`}
    >
      <CardContent className="p-6">
        <div className="space-y-4">
          {/* Header */}
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <div
                className={`rounded-full p-2 ${character.isNarrator ? 'bg-primary/10' : 'bg-muted'}`}
              >
                <User className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-lg font-semibold">
                  {character.displayName}
                </h3>
                <p className="text-muted-foreground text-sm">
                  {character.isNarrator
                    ? 'Narrator / Stage Directions'
                    : 'Character'}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {isAssigned ? (
                <CheckCircle2 className="h-5 w-5 text-green-500" />
              ) : (
                <Circle className="text-muted-foreground h-5 w-5" />
              )}
            </div>
          </div>

          {/* Character Info */}
          {(character.role || character.castingNotes) && (
            <div className="bg-muted/50 space-y-2 rounded-md p-3">
              {character.role && (
                <div className="space-y-1">
                  <p className="text-muted-foreground text-xs font-medium">
                    Role
                  </p>
                  <p className="text-sm">{character.role}</p>
                </div>
              )}
              {character.castingNotes && (
                <div className="space-y-1">
                  <p className="text-muted-foreground text-xs font-medium">
                    Casting Notes
                  </p>
                  <p className="text-sm">{character.castingNotes}</p>
                </div>
              )}
            </div>
          )}

          {/* Stats */}
          <div className="grid grid-cols-3 gap-3 text-sm">
            <div className="space-y-1">
              <div className="text-muted-foreground flex items-center gap-1">
                <MessageSquare className="h-3 w-3" />
                <span>Lines</span>
              </div>
              <p className="font-medium">{character.lineCount}</p>
            </div>
            <div className="space-y-1">
              <p className="text-muted-foreground">Characters</p>
              <p className="font-medium">
                {character.totalCharacters.toLocaleString()}
              </p>
            </div>
            <div className="space-y-1">
              <p className="text-muted-foreground">Longest</p>
              <p className="font-medium">{character.longestDialogue} chars</p>
            </div>
          </div>

          {/* Voice Assignment */}
          <div className="space-y-2">
            {isAssigned ? (
              <div className="bg-muted space-y-2 rounded-md p-3">
                <div className="flex items-center gap-2">
                  <Mic className="text-muted-foreground h-4 w-4" />
                  <span className="text-sm font-medium">
                    {character.assignedVoice.voiceName}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant="secondary" className="text-xs">
                    {character.assignedVoice.provider}
                  </Badge>
                  <span className="text-muted-foreground text-xs">
                    {character.assignedVoice.voiceId}
                  </span>
                </div>
              </div>
            ) : (
              <div className="border-muted rounded-md border-2 border-dashed p-3 text-center">
                <p className="text-muted-foreground text-sm">
                  No voice assigned
                </p>
              </div>
            )}

            <Button
              onClick={onAssignVoice}
              variant={isAssigned ? 'outline' : 'default'}
              className="w-full"
            >
              {isAssigned ? 'Change Voice' : 'Assign Voice'}
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
