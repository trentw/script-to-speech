import { AlertTriangle, Check, Info, Settings } from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { appButtonVariants } from '@/components/ui/button-variants';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { WorkspaceDebugInfo } from '@/components/WorkspaceDebugInfo';
import { useEnvKeys, useUpdateEnvKey } from '@/hooks/queries/useEnvKeys';
import type { SettingsSection } from '@/stores/appStore';
import { useLayout } from '@/stores/appStore';

// Provider configuration grouped by provider
// Only multi-key providers (Minimax) will show a provider header
const PROVIDER_GROUPS = [
  {
    provider: 'OpenAI',
    keys: [{ key: 'OPENAI_API_KEY', label: 'API Key' }],
  },
  {
    provider: 'ElevenLabs',
    keys: [{ key: 'ELEVEN_API_KEY', label: 'API Key' }],
  },
  {
    provider: 'Cartesia',
    keys: [{ key: 'CARTESIA_API_KEY', label: 'API Key' }],
  },
  {
    provider: 'Minimax',
    keys: [
      { key: 'MINIMAX_API_KEY', label: 'API Key' },
      { key: 'MINIMAX_GROUP_ID', label: 'Group ID' },
    ],
  },
  {
    provider: 'Zonos',
    keys: [{ key: 'ZONOS_API_KEY', label: 'API Key' }],
  },
];

// Section identifiers matching SettingsSection type
const SECTION_IDS = {
  API_KEYS: 'api-keys' as const,
  DEBUG: 'debug' as const,
};

export function SettingsDialog() {
  const { activeModal, closeModal } = useLayout();
  const { data: envKeys, isLoading } = useEnvKeys();
  const updateKey = useUpdateEnvKey();

  const [formData, setFormData] = useState<Record<string, string>>({});
  const [editingKeys, setEditingKeys] = useState<Record<string, boolean>>({});
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Refs for scroll-into-view
  const apiKeysRef = useRef<HTMLDivElement>(null);
  const debugRef = useRef<HTMLDivElement>(null);

  // Track if we've scrolled for this dialog session (prevents re-scroll on manual expansion)
  const hasScrolledRef = useRef(false);

  // Memoize to prevent recreation on every render
  const sectionRefs = useMemo<
    Record<SettingsSection, React.RefObject<HTMLDivElement>>
  >(
    () => ({
      'api-keys': apiKeysRef,
      debug: debugRef,
    }),
    []
  );

  // Check if settings modal is open and get section
  const isOpen = activeModal?.type === 'settings';
  const targetSection =
    activeModal?.type === 'settings' ? activeModal.section : undefined;

  // Control accordion state - expand target section if specified
  const [expandedSections, setExpandedSections] = useState<string[]>([]);

  // Update expanded sections when target section changes
  useEffect(() => {
    if (isOpen && targetSection) {
      setExpandedSections((prev) => {
        if (!prev.includes(targetSection)) {
          return [...prev, targetSection];
        }
        return prev;
      });
    }
  }, [isOpen, targetSection]);

  // Scroll to target section ONLY on initial anchor navigation (not manual expansion)
  useEffect(() => {
    if (
      isOpen &&
      targetSection &&
      !hasScrolledRef.current &&
      sectionRefs[targetSection]?.current
    ) {
      hasScrolledRef.current = true;
      // Delay to allow accordion animation to complete
      const timer = setTimeout(() => {
        sectionRefs[targetSection].current?.scrollIntoView({
          behavior: 'smooth',
          block: 'start',
        });
      }, 150);

      return () => clearTimeout(timer);
    }
  }, [isOpen, targetSection, sectionRefs]);

  // Reset state when dialog closes
  useEffect(() => {
    if (!isOpen) {
      setExpandedSections([]);
      hasScrolledRef.current = false;
    }
  }, [isOpen]);

  const handleEdit = (key: string) => {
    setEditingKeys((prev) => ({ ...prev, [key]: true }));
  };

  const handleSave = async (key: string) => {
    const value = formData[key];
    if (!value || !value.trim()) {
      return;
    }

    try {
      await updateKey.mutateAsync({ key, value: value.trim() });

      // Clear the input field and editing state
      setFormData((prev) => ({ ...prev, [key]: '' }));
      setEditingKeys((prev) => ({ ...prev, [key]: false }));

      // Show success message
      setSuccessMessage(`${key} saved successfully`);
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (error) {
      // Error handling is done by React Query
      console.error('Failed to save API key:', error);
    }
  };

  const handleKeyPress = (
    e: React.KeyboardEvent<HTMLInputElement>,
    key: string
  ) => {
    if (e.key === 'Enter') {
      handleSave(key);
    }
  };

  // Get env file path from the envKeys data
  const envPath = envKeys?._envPath as string | undefined;

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && closeModal()}>
      <DialogContent className="flex h-[80vh] max-h-[80vh] flex-col sm:max-w-3xl">
        {/* Fixed header - stays at top */}
        <DialogHeader className="border-border flex-shrink-0 border-b pb-4">
          <DialogTitle className="flex items-center gap-2">
            <Settings className="h-5 w-5" />
            Settings
          </DialogTitle>
        </DialogHeader>

        {/* Scrollable content area */}
        <div className="flex-1 space-y-6 overflow-y-auto py-4 pr-4">
          {/* Success message */}
          {successMessage && (
            <Alert className="border-green-200 bg-green-50">
              <Check className="h-4 w-4 text-green-600" />
              <AlertTitle className="text-green-900">Success</AlertTitle>
              <AlertDescription className="text-green-800">
                {successMessage}
              </AlertDescription>
            </Alert>
          )}

          {/* Warning about API key errors */}
          {updateKey.isError && (
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertTitle>Error</AlertTitle>
              <AlertDescription>
                {updateKey.error?.message || 'Failed to save API key'}
              </AlertDescription>
            </Alert>
          )}

          {/* Accordion Sections */}
          <Accordion
            type="multiple"
            value={expandedSections}
            onValueChange={setExpandedSections}
            className="w-full"
          >
            {/* TTS Provider API Keys Section */}
            <AccordionItem
              value={SECTION_IDS.API_KEYS}
              ref={apiKeysRef}
              className="scroll-mt-4"
            >
              <AccordionTrigger className="text-sm font-semibold">
                TTS Provider API Keys
              </AccordionTrigger>
              <AccordionContent>
                {isLoading ? (
                  <div className="text-muted-foreground text-sm">
                    Loading API keys...
                  </div>
                ) : (
                  <div className="space-y-4">
                    {PROVIDER_GROUPS.map(({ provider, keys }) => (
                      <Card key={provider}>
                        {/* Only show card header for multi-key providers */}
                        {keys.length > 1 && (
                          <CardHeader className="pb-4">
                            <CardTitle className="text-base">
                              {provider}
                            </CardTitle>
                          </CardHeader>
                        )}

                        <CardContent className="pt-0">
                          <div className="space-y-4">
                            {keys.map(({ key, label }) => {
                              const isConfigured = envKeys?.[key];
                              const isEditing = editingKeys[key];
                              const maskedValue =
                                typeof isConfigured === 'string'
                                  ? isConfigured
                                  : '';

                              // For single-key providers, show "Provider API Key"
                              // For multi-key providers, just show the label (e.g., "API Key", "Group ID")
                              const displayLabel =
                                keys.length === 1
                                  ? `${provider} ${label}`
                                  : label;

                              return (
                                <div key={key} className="space-y-2">
                                  <div className="flex items-center justify-between">
                                    <Label htmlFor={key} className="text-sm">
                                      {displayLabel}
                                    </Label>
                                    {isConfigured && !isEditing && (
                                      <Badge
                                        variant="outline"
                                        className="border-green-200 bg-green-50 text-green-700"
                                      >
                                        <Check className="mr-1 h-3 w-3" />
                                        Configured
                                      </Badge>
                                    )}
                                  </div>

                                  <div className="flex gap-2">
                                    <Input
                                      id={key}
                                      type={
                                        isConfigured && !isEditing
                                          ? 'text'
                                          : 'password'
                                      }
                                      disabled={isConfigured && !isEditing}
                                      placeholder={
                                        isConfigured && !isEditing
                                          ? maskedValue
                                          : 'Enter API key'
                                      }
                                      value={formData[key] || ''}
                                      onChange={(e) =>
                                        setFormData((prev) => ({
                                          ...prev,
                                          [key]: e.target.value,
                                        }))
                                      }
                                      onKeyPress={(e) => handleKeyPress(e, key)}
                                      className="flex-1"
                                    />
                                    {isConfigured && !isEditing ? (
                                      <button
                                        className={appButtonVariants({
                                          variant: 'secondary',
                                          size: 'sm',
                                        })}
                                        onClick={() => handleEdit(key)}
                                      >
                                        Change
                                      </button>
                                    ) : (
                                      <button
                                        className={appButtonVariants({
                                          variant: 'primary',
                                          size: 'sm',
                                        })}
                                        onClick={() => handleSave(key)}
                                        disabled={
                                          !formData[key]?.trim() ||
                                          updateKey.isPending
                                        }
                                      >
                                        {updateKey.isPending
                                          ? 'Saving...'
                                          : 'Save'}
                                      </button>
                                    )}
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        </CardContent>
                      </Card>
                    ))}

                    {/* Info alert about .env file */}
                    <Alert>
                      <Info className="h-4 w-4" />
                      <AlertDescription className="text-xs">
                        API keys are stored in the{' '}
                        <code className="bg-muted rounded px-1 py-0.5">
                          .env
                        </code>{' '}
                        file
                        {envPath && (
                          <>
                            {' '}
                            at{' '}
                            <code className="bg-muted rounded px-1 py-0.5 text-xs break-all">
                              {envPath}
                            </code>
                          </>
                        )}{' '}
                        and shared between GUI and CLI.
                      </AlertDescription>
                    </Alert>
                  </div>
                )}
              </AccordionContent>
            </AccordionItem>

            {/* Debug Information Section */}
            <AccordionItem
              value={SECTION_IDS.DEBUG}
              ref={debugRef}
              className="scroll-mt-4"
            >
              <AccordionTrigger className="text-sm font-semibold">
                Debug Information
              </AccordionTrigger>
              <AccordionContent>
                <WorkspaceDebugInfo />
              </AccordionContent>
            </AccordionItem>
          </Accordion>
        </div>
      </DialogContent>
    </Dialog>
  );
}
