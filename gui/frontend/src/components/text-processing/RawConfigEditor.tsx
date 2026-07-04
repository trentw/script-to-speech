import React from 'react';

import { Textarea } from '@/components/ui/textarea';

interface RawConfigEditorProps {
  configYaml: string;
  onChange: (configYaml: string) => void;
}

/**
 * Raw YAML editor for an entry's config sub-tree. Used for unknown
 * processors and as the per-entry "Edit as YAML" escape hatch. YAML stays
 * opaque to the frontend; the backend parses and validates it.
 */
export const RawConfigEditor: React.FC<RawConfigEditorProps> = ({
  configYaml,
  onChange,
}) => {
  return (
    <div className="space-y-1">
      <Textarea
        value={configYaml}
        spellCheck={false}
        rows={Math.min(16, Math.max(4, configYaml.split('\n').length + 1))}
        className="font-mono text-xs"
        placeholder={'# YAML config for this processor\n'}
        onChange={(e) => onChange(e.target.value)}
      />
      <p className="text-muted-foreground text-xs">
        Edit this entry's config as YAML. Validated when you save.
      </p>
    </div>
  );
};
