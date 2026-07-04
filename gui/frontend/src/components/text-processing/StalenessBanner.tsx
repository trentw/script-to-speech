import { AlertCircle, RefreshCw, Wand2 } from 'lucide-react';
import React, { useState } from 'react';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';

import type { TextProcessorConfig } from '../../types/text-processing';

interface StalenessBannerProps {
  config: TextProcessorConfig;
  onConvert: () => void;
  onReseed: () => void;
  isConverting: boolean;
}

/**
 * Banner for configs needing attention: legacy additive files (offer
 * conversion to an editable standalone config) and configs seeded from an
 * older version of the shipped defaults (offer re-seeding).
 */
export const StalenessBanner: React.FC<StalenessBannerProps> = ({
  config,
  onConvert,
  onReseed,
  isConverting,
}) => {
  const [dismissed, setDismissed] = useState(false);

  if (dismissed) return null;

  if (config.is_legacy_additive) {
    return (
      <Alert>
        <Wand2 className="h-4 w-4" />
        <AlertDescription className="flex flex-wrap items-center justify-between gap-2">
          <span>
            This project uses a <strong>legacy add-on config</strong> that runs
            on top of the built-in defaults. Convert it to see and edit the full
            pipeline here (processing behavior is unchanged).
          </span>
          <span className="flex gap-2">
            <Button size="sm" onClick={onConvert} disabled={isConverting}>
              {isConverting ? 'Converting…' : 'Convert to editable config'}
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setDismissed(true)}
            >
              Not now
            </Button>
          </span>
        </AlertDescription>
      </Alert>
    );
  }

  if (config.stale) {
    return (
      <Alert variant="warning">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription className="flex flex-wrap items-center justify-between gap-2">
          <span>
            This config was created from an <strong>older version</strong> of
            the built-in defaults
            {config.metadata?.seeded_by_version
              ? ` (seeded with Script to Speech ${config.metadata.seeded_by_version})`
              : ''}
            . Your settings still work; re-seed to pick up the latest defaults
            (this discards your customizations).
          </span>
          <span className="flex gap-2">
            <Button size="sm" variant="outline" onClick={onReseed}>
              <RefreshCw className="mr-1 h-4 w-4" />
              Re-seed from current defaults
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setDismissed(true)}
            >
              Dismiss
            </Button>
          </span>
        </AlertDescription>
      </Alert>
    );
  }

  return null;
};
