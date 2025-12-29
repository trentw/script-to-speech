import { User } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import type { SpeakerGroup } from '@/types/review';

import { DialogueItem } from './DialogueItem';

interface SpeakerGroupComponentProps {
  group: SpeakerGroup;
  projectName: string;
  cacheFolder: string;
  showDbfs?: boolean;
}

/**
 * Displays a group of clips for a single speaker.
 */
export function SpeakerGroupComponent({
  group,
  projectName,
  cacheFolder,
  showDbfs = false,
}: SpeakerGroupComponentProps) {
  return (
    <div className="border-border rounded-lg border p-4">
      {/* Speaker Header */}
      <div className="mb-3 flex items-center gap-2">
        <User className="text-muted-foreground h-4 w-4" />
        <span className="font-medium">{group.speaker}</span>
        <Badge variant="secondary" className="text-xs">
          {group.voiceId}
        </Badge>
        <Badge variant="outline" className="text-xs">
          {group.provider}
        </Badge>
        <span className="text-muted-foreground ml-auto text-sm">
          {group.clips.length} clip{group.clips.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Clips List */}
      <div className="space-y-3">
        {group.clips.map((clip) => (
          <DialogueItem
            key={clip.cacheFilename}
            clip={clip}
            projectName={projectName}
            cacheFolder={cacheFolder}
            showDbfs={showDbfs}
          />
        ))}
      </div>
    </div>
  );
}
