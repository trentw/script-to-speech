import { AlertTriangle } from 'lucide-react';
import React, { useEffect, useState } from 'react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { appButtonVariants } from '@/components/ui/button-variants';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';

interface PrivacyWarningProps {
  message?: string;
  checked?: boolean;
  onCheckedChange?: (checked: boolean) => void;
  isModal?: boolean;
  onAccept?: () => void;
  onCancel?: () => void;
}

const DEFAULT_MESSAGE = `This feature requires sending your screenplay data to an external Large Language Model (LLM) service.

Please note:
• Your screenplay content will be processed by the LLM provider
• The provider may retain this data according to their privacy policy
• Sensitive or confidential content should not be processed
• You are responsible for compliance with any applicable agreements

By proceeding, you acknowledge these privacy implications.`;

export function PrivacyWarning({
  message = DEFAULT_MESSAGE,
  checked = false,
  onCheckedChange,
  isModal = false,
  onAccept,
  onCancel,
}: PrivacyWarningProps) {
  const [localChecked, setLocalChecked] = useState(checked);

  useEffect(() => {
    setLocalChecked(checked);
  }, [checked]);

  const handleCheckedChange = (value: boolean) => {
    setLocalChecked(value);
    onCheckedChange?.(value);
  };

  const handleAccept = () => {
    onAccept?.();
  };

  const handleCancel = () => {
    onCancel?.();
  };

  const handleOpenChange = (open: boolean) => {
    if (!open) {
      onCancel?.();
    }
  };

  if (isModal) {
    return (
      <Dialog open={isModal} onOpenChange={handleOpenChange}>
        <DialogContent className="border bg-white shadow-lg sm:max-w-[525px]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-amber-600 dark:text-amber-400" />
              Privacy Notice
            </DialogTitle>
            <DialogDescription className="sr-only">
              Important privacy information about using LLM services
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="text-muted-foreground text-sm whitespace-pre-wrap">
              {message}
            </div>
            <div className="flex items-center space-x-2">
              <Checkbox
                id="privacy-consent-modal"
                checked={localChecked}
                onCheckedChange={handleCheckedChange}
              />
              <Label
                htmlFor="privacy-consent-modal"
                className="text-sm leading-none font-medium peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
              >
                I understand and accept the privacy implications
              </Label>
            </div>
          </div>
          <DialogFooter>
            <button
              className={appButtonVariants({
                variant: 'secondary',
                size: 'default',
              })}
              onClick={handleCancel}
            >
              Cancel
            </button>
            <button
              className={appButtonVariants({
                variant: 'primary',
                size: 'default',
              })}
              onClick={handleAccept}
              disabled={!localChecked}
            >
              Continue
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    );
  }

  return (
    <Alert className="border-amber-200 bg-amber-50 dark:border-amber-900 dark:bg-amber-950">
      <AlertTriangle className="h-4 w-4 text-amber-600 dark:text-amber-400" />
      <AlertTitle className="text-amber-900 dark:text-amber-100">
        Privacy Notice
      </AlertTitle>
      <AlertDescription className="space-y-4">
        <div className="text-sm whitespace-pre-wrap text-amber-800 dark:text-amber-200">
          {message}
        </div>
        {onCheckedChange && (
          <div className="flex items-center space-x-2">
            <Checkbox
              id="privacy-consent"
              checked={localChecked}
              onCheckedChange={handleCheckedChange}
            />
            <Label
              htmlFor="privacy-consent"
              className="text-sm leading-none font-medium peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
            >
              I understand and accept the privacy implications
            </Label>
          </div>
        )}
      </AlertDescription>
    </Alert>
  );
}
