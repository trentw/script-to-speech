import { AlertCircle, Download, Loader2 } from 'lucide-react';
import React, { useState } from 'react';

import { downloadAudio } from '../../utils/audioUtils';
import type { AppButtonSize, AppButtonVariant } from './button-variants';
import { appButtonVariants } from './button-variants';
import { Tooltip, TooltipContent, TooltipTrigger } from './tooltip';

interface DownloadButtonProps {
  /** The URL to download */
  url: string;
  /** Filename for the downloaded file */
  filename?: string;
  /** Button variant for styling */
  variant?: AppButtonVariant;
  /** Button size */
  size?: AppButtonSize;
  /** Icon only (no text) */
  iconOnly?: boolean;
  /** Disabled state */
  disabled?: boolean;
  /** Custom tooltip text */
  tooltip?: string;
  /** Success callback */
  onSuccess?: () => void;
  /** Error callback */
  onError?: (error: string) => void;
  /** Custom class name */
  className?: string;
  /** Click event handler for parent components */
  onClick?: (e: React.MouseEvent) => void;
}

export const DownloadButton: React.FC<DownloadButtonProps> = ({
  url,
  filename,
  variant = 'list-action',
  size = 'icon-sm',
  iconOnly = true,
  disabled = false,
  tooltip = 'Download audio',
  onSuccess,
  onError,
  className = '',
  onClick,
}) => {
  const [isDownloading, setIsDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleDownload = async (e: React.MouseEvent) => {
    e.stopPropagation();

    // Call parent onClick if provided
    if (onClick) {
      onClick(e);
    }

    if (disabled || isDownloading) return;

    setIsDownloading(true);
    setError(null);

    try {
      await downloadAudio(url, filename);
      onSuccess?.();
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Download failed';
      setError(errorMessage);
      onError?.(errorMessage);
      console.error('Download error:', err);
    } finally {
      setIsDownloading(false);
    }
  };

  const getIcon = () => {
    if (isDownloading) {
      return <Loader2 className={iconOnly ? 'h-3 w-3' : 'mr-1 h-3 w-3'} />;
    }
    if (error) {
      return <AlertCircle className={iconOnly ? 'h-3 w-3' : 'mr-1 h-3 w-3'} />;
    }
    return <Download className={iconOnly ? 'h-3 w-3' : 'mr-1 h-3 w-3'} />;
  };

  const buttonContent = (
    <button
      className={`${appButtonVariants({ variant, size })} ${className}`}
      onClick={handleDownload}
      disabled={disabled || isDownloading}
      aria-label={tooltip}
    >
      {getIcon()}
      {!iconOnly && (
        <span>
          {isDownloading ? 'Downloading...' : error ? 'Retry' : 'Download'}
        </span>
      )}
    </button>
  );

  // Wrap with tooltip if iconOnly
  if (iconOnly) {
    return (
      <Tooltip>
        <TooltipTrigger asChild>{buttonContent}</TooltipTrigger>
        <TooltipContent>
          <p>
            {isDownloading
              ? 'Downloading...'
              : error
                ? `Error: ${error}`
                : tooltip}
          </p>
        </TooltipContent>
      </Tooltip>
    );
  }

  return buttonContent;
};

// Preset variants for common use cases
export const DownloadButtonPresets = {
  /** Small icon button for list items */
  listItem: {
    variant: 'list-action' as const,
    size: 'icon-sm' as const,
    iconOnly: true,
  },
  /** Medium icon button for audio controls */
  audioControl: {
    variant: 'audio-control' as const,
    size: 'icon-md' as const,
    iconOnly: true,
  },
  /** Text button with icon */
  textButton: {
    variant: 'secondary' as const,
    size: 'sm' as const,
    iconOnly: false,
  },
  /** Primary action button */
  primary: {
    variant: 'primary' as const,
    size: 'default' as const,
    iconOnly: false,
  },
} as const;
