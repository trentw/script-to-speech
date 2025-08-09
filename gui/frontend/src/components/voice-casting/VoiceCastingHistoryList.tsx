import { CheckCircle2, Circle, Wand2 } from 'lucide-react';

import { Card } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';

interface VoiceCastingSession {
  sessionId: string;
  screenplayName: string;
  status: 'in-progress' | 'completed';
  assignedCount: number;
  totalCount: number;
  lastUpdated: number;
}

interface VoiceCastingHistoryListProps {
  sessions: VoiceCastingSession[];
  onSelect: (sessionId: string) => void;
  selectedId?: string;
}

export function VoiceCastingHistoryList({
  sessions,
  onSelect,
  selectedId,
}: VoiceCastingHistoryListProps) {
  if (sessions.length === 0) {
    return (
      <Card className="p-6 text-center">
        <Wand2 className="text-muted-foreground mx-auto mb-4 h-12 w-12" />
        <p className="text-muted-foreground">No casting sessions yet</p>
      </Card>
    );
  }

  return (
    <ScrollArea className="h-[400px]">
      <div className="space-y-2">
        {sessions.map((session) => {
          const isSelected = session.sessionId === selectedId;
          const isCompleted = session.status === 'completed';

          return (
            <Card
              key={session.sessionId}
              className={cn(
                'hover:bg-accent cursor-pointer p-4 transition-colors',
                isSelected && 'border-primary bg-accent'
              )}
              onClick={() => onSelect(session.sessionId)}
            >
              <div className="space-y-2">
                {/* Title and Status */}
                <div className="flex items-start justify-between">
                  <h4 className="truncate font-semibold">
                    {session.screenplayName}
                  </h4>
                  {isCompleted ? (
                    <CheckCircle2 className="h-4 w-4 flex-shrink-0 text-green-600" />
                  ) : (
                    <Circle className="text-muted-foreground h-4 w-4 flex-shrink-0" />
                  )}
                </div>

                {/* Assignment Progress */}
                <div className="flex items-center gap-4 text-sm">
                  <span
                    className={cn(
                      'text-muted-foreground',
                      isCompleted && 'text-green-600'
                    )}
                  >
                    {session.assignedCount}/{session.totalCount} assigned
                  </span>
                </div>
              </div>
            </Card>
          );
        })}
      </div>
    </ScrollArea>
  );
}
