import { FileText, MessageSquare, Users } from 'lucide-react';

import { Card } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';

interface ScreenplayHistoryListProps {
  screenplays: any[];
  onSelect: (screenplay: any) => void;
  selectedId?: string;
}

export function ScreenplayHistoryList({
  screenplays,
  onSelect,
  selectedId,
}: ScreenplayHistoryListProps) {
  if (screenplays.length === 0) {
    return (
      <Card className="p-6 text-center">
        <FileText className="text-muted-foreground mx-auto mb-4 h-12 w-12" />
        <p className="text-muted-foreground">No screenplays parsed yet</p>
      </Card>
    );
  }

  return (
    <ScrollArea className="h-[400px]">
      <div className="space-y-2">
        {screenplays.map((screenplay) => {
          const isSelected = screenplay.task_id === selectedId;
          const analysis = screenplay.analysis || {};

          return (
            <Card
              key={screenplay.task_id}
              className={cn(
                'hover:bg-accent cursor-pointer p-4 transition-colors',
                isSelected && 'border-primary bg-accent'
              )}
              onClick={() => onSelect(screenplay)}
            >
              <div className="space-y-2">
                {/* Title */}
                <div>
                  <h4 className="truncate font-semibold">
                    {screenplay.screenplay_name}
                  </h4>
                  <p className="text-muted-foreground truncate text-xs">
                    {screenplay.filename}
                  </p>
                </div>

                {/* Stats */}
                <div className="flex items-center gap-4 text-sm">
                  <div className="flex items-center gap-1">
                    <Users className="text-muted-foreground h-3 w-3" />
                    <span>
                      {analysis.total_distinct_speakers || 0} speakers
                    </span>
                  </div>
                  <div className="flex items-center gap-1">
                    <MessageSquare className="text-muted-foreground h-3 w-3" />
                    <span>{analysis.total_chunks || 0} chunks</span>
                  </div>
                </div>
              </div>
            </Card>
          );
        })}
      </div>
    </ScrollArea>
  );
}

// Add the missing cn utility import
import { cn } from '@/lib/utils';
