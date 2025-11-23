import { AlertTriangle } from 'lucide-react';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { appButtonVariants } from '@/components/ui/button-variants';
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { useLayout } from '@/stores/appStore';

interface ApiKeyWarningProps {
  open: boolean;
  onClose: () => void;
  provider: string;
  providerDisplayName?: string;
}

/**
 * Warning dialog shown when user attempts to use a provider without configured API key
 * Provides options to cancel or open settings to configure the key
 */
export function ApiKeyWarning({
  open,
  onClose,
  provider,
  providerDisplayName,
}: ApiKeyWarningProps) {
  const { setActiveModal } = useLayout();

  const displayName = providerDisplayName || provider;

  const handleOpenSettings = () => {
    onClose();
    setActiveModal('settings');
  };

  return (
    <Dialog open={open} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-amber-600" />
            API Key Required
          </DialogTitle>
        </DialogHeader>

        <Alert variant="warning" className="border-amber-200 bg-amber-50">
          <AlertDescription className="text-amber-900">
            The API key for <strong>{displayName}</strong> has not been
            configured. Please add it in settings to use this provider.
          </AlertDescription>
        </Alert>

        <DialogFooter>
          <button
            className={appButtonVariants({ variant: 'secondary' })}
            onClick={onClose}
          >
            Cancel
          </button>
          <button
            className={appButtonVariants({ variant: 'primary' })}
            onClick={handleOpenSettings}
          >
            Open Settings
          </button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
