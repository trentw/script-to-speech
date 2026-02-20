import {
  AlertCircle,
  ArrowLeft,
  Hash,
  Loader2,
  MessageSquare,
} from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';

import { ApiKeyWarning } from '@/components/settings/ApiKeyWarning';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { appButtonVariants } from '@/components/ui/button-variants';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { TooltipProvider } from '@/components/ui/tooltip';
import { isProviderConfigured } from '@/constants/providers';
import { useAssignVoice } from '@/hooks/mutations/useAssignVoice';
import { useProviders, useVoiceLibrary } from '@/hooks/queries';
import { useValidateApiKeys } from '@/hooks/queries/useEnvKeys';
import { useSessionAssignments } from '@/hooks/queries/useSessionAssignments';
import { useResolveVoiceEntry } from '@/hooks/useResolveVoiceEntry';
import { useVoiceCastingUI } from '@/stores/uiStore';
import type { VoiceEntry } from '@/types';
import type { VoiceAssignment } from '@/types/voice-casting';
import { calculateVoiceUsage } from '@/utils/voiceUsageHelper';

import { CustomVoiceCard } from './CustomVoiceCard';
import { TruncatedNote } from './TruncatedNote';
import { VoiceCard } from './VoiceCard';

interface CharacterData {
  name: string;
  displayName: string;
  lineCount: number;
  totalCharacters: number;
  longestDialogue: number;
  isNarrator: boolean;
  role?: string;
  castingNotes?: string;
  additionalNotes?: string[];
  assignedVoice: {
    provider: string;
    voiceName: string;
    voiceId: string;
  } | null;
}

interface VoiceAssignmentPanelProps {
  sessionId: string;
  characterName: string;
  character: CharacterData;
  onBack: () => void;
  onAssign: () => void;
}

export function VoiceAssignmentPanel({
  sessionId,
  characterName,
  character,
  onBack,
  onAssign,
}: VoiceAssignmentPanelProps) {
  // All hooks must be called at the top level before any early returns
  const {
    data: providers,
    isPending: providersLoading,
    error: providersError,
  } = useProviders();

  // Fetch session data using React Query
  const {
    data: sessionData,
    isLoading: sessionLoading,
    error: sessionError,
  } = useSessionAssignments(sessionId);

  // Voice assignment mutation
  const assignVoiceMutation = useAssignVoice();

  // Fetch API key validation status
  const { data: apiKeyStatus } = useValidateApiKeys();

  // State for API key warning dialog
  const [showApiKeyWarning, setShowApiKeyWarning] = useState(false);

  // UI state for filters (stored in UI store)
  const { filterProvider, setFilterProvider } = useVoiceCastingUI();

  // Get current assignment from session data
  const currentAssignment = sessionData?.assignments?.get(characterName);

  // Detect replace mode: assignment exists with actual voice data
  const isReplaceMode = !!(
    currentAssignment?.provider &&
    (currentAssignment?.sts_id || currentAssignment?.provider_config)
  );

  // Resolve the current voice entry for display in replace mode
  const currentVoiceEntry = useResolveVoiceEntry(
    currentAssignment?.provider,
    currentAssignment?.sts_id
  );

  // Initialize state with current assignment or stable provider default
  const [selectedProvider, setSelectedProvider] = useState<string>(
    currentAssignment?.provider || filterProvider || 'openai'
  );

  const [customVoiceConfig, setCustomVoiceConfig] = useState<
    Record<string, unknown>
  >(currentAssignment?.provider_config || {});

  // Scroll to top on mount (prevents inheriting scroll position from previous page)
  const topRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    topRef.current?.scrollIntoView({ block: 'start' });
  }, []);

  // Update selected provider when providers load, preferring stable providers
  useEffect(() => {
    if (providers && providers.length > 0 && !currentAssignment?.provider) {
      // Only use openai or elevenlabs as they are stable
      const stableProvider =
        providers.find((p) => p.identifier === 'openai') ||
        providers.find((p) => p.identifier === 'elevenlabs');
      if (stableProvider) {
        setSelectedProvider(stableProvider.identifier);
      }
    }
  }, [providers, currentAssignment?.provider]);

  // Update UI store filter when provider changes
  useEffect(() => {
    setFilterProvider(selectedProvider);
  }, [selectedProvider, setFilterProvider]);

  // Load voices for the selected provider
  const {
    data: providerVoices,
    isPending: voicesLoading,
    error: voicesError,
  } = useVoiceLibrary(selectedProvider);

  // Use the voices directly from the hook
  const voiceList = useMemo(() => providerVoices || [], [providerVoices]);

  // Calculate voice usage map
  const voiceUsageMap = useMemo(() => {
    if (!sessionData) return new Map();
    return calculateVoiceUsage(
      sessionData.assignments || new Map(),
      sessionData.characters || new Map(),
      characterName
    );
  }, [sessionData, characterName]);

  // Guard against loading and error states AFTER all hooks
  if (sessionLoading) {
    return (
      <div className="container mx-auto max-w-6xl space-y-6 p-6">
        <div className="flex h-64 items-center justify-center">
          <Loader2 className="text-muted-foreground h-6 w-6 animate-spin" />
        </div>
      </div>
    );
  }

  if (sessionError) {
    return (
      <div className="container mx-auto max-w-6xl space-y-6 p-6">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Failed to load session data: {sessionError.message}
          </AlertDescription>
        </Alert>
        <button
          className={appButtonVariants({
            variant: 'secondary',
            size: 'sm',
          })}
          onClick={onBack}
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </button>
      </div>
    );
  }

  if (!sessionData) {
    return (
      <div className="container mx-auto max-w-6xl space-y-6 p-6">
        <Alert>
          <AlertDescription>
            No session data available. Please select or create a session first.
          </AlertDescription>
        </Alert>
        <button
          className={appButtonVariants({
            variant: 'secondary',
            size: 'sm',
          })}
          onClick={onBack}
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </button>
      </div>
    );
  }

  const handleLibraryVoiceAssign = async (voice: VoiceEntry) => {
    // Check if provider has required API keys configured
    if (apiKeyStatus && !isProviderConfigured(selectedProvider, apiKeyStatus)) {
      setShowApiKeyWarning(true);
      return;
    }

    if (!sessionData.yamlVersionId) {
      console.error('Cannot assign voice: missing version ID');
      return;
    }

    const assignment: VoiceAssignment = {
      character: characterName,
      provider: selectedProvider,
      sts_id: voice.sts_id,
    };

    try {
      await assignVoiceMutation.mutateAsync({
        sessionId,
        character: characterName,
        assignment,
        versionId: sessionData.yamlVersionId,
      });
      onAssign();
    } catch (error) {
      console.error('Failed to assign voice:', error);
      // Error handling is managed by the mutation
    }
  };

  const handleCustomVoiceAssign = async (config: Record<string, unknown>) => {
    // Check if provider has required API keys configured
    if (apiKeyStatus && !isProviderConfigured(selectedProvider, apiKeyStatus)) {
      setShowApiKeyWarning(true);
      return;
    }

    if (!sessionData.yamlVersionId) {
      console.error('Cannot assign voice: missing version ID');
      return;
    }

    const assignment: VoiceAssignment = {
      character: characterName,
      provider: selectedProvider,
      sts_id: '', // Empty string for custom voices as per backend model
      provider_config: config,
    };

    try {
      await assignVoiceMutation.mutateAsync({
        sessionId,
        character: characterName,
        assignment,
        versionId: sessionData.yamlVersionId,
      });
      onAssign();
    } catch (error) {
      console.error('Failed to assign custom voice:', error);
      // Error handling is managed by the mutation
    }
  };

  const isLoading = providersLoading || voicesLoading;

  return (
    <TooltipProvider>
      <div ref={topRef} className="container mx-auto max-w-6xl space-y-6 p-6">
        {/* Header */}
        <div className="flex items-center gap-4">
          <button
            className={appButtonVariants({
              variant: 'secondary',
              size: 'icon',
            })}
            onClick={onBack}
          >
            <ArrowLeft className="h-4 w-4" />
          </button>
          <div className="flex-1">
            <h1 className="text-2xl font-bold">
              {character.displayName}:{' '}
              {isReplaceMode ? 'Replace Voice' : 'Assign Voice'}
            </h1>
            <div className="text-muted-foreground flex items-center gap-3">
              <div className="flex items-center gap-1">
                <MessageSquare className="h-4 w-4" />
                <span>{character.lineCount} lines</span>
              </div>
              <div className="flex items-center gap-1">
                <Hash className="h-4 w-4" />
                <span>
                  {character.totalCharacters.toLocaleString()} characters
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Character Notes */}
        {(character.role ||
          character.castingNotes ||
          character.additionalNotes?.length) && (
          <div className="bg-muted/50 space-y-1.5 rounded-md p-3">
            {character.role && (
              <TruncatedNote
                text={character.role}
                maxLines={2}
                className="text-sm font-medium"
              />
            )}
            {character.castingNotes && (
              <TruncatedNote
                text={character.castingNotes}
                maxLines={3}
                className="text-muted-foreground text-sm"
              />
            )}
            {character.additionalNotes &&
              character.additionalNotes.length > 0 && (
                <>
                  <div className="border-muted-foreground/20 border-t pt-1.5">
                    <p className="text-muted-foreground mb-1 text-xs font-medium">
                      Additional Notes
                    </p>
                    <div className="space-y-0.5">
                      {character.additionalNotes.map((note, idx) => (
                        <TruncatedNote
                          key={idx}
                          text={note}
                          maxLines={1}
                          className="text-muted-foreground text-sm"
                        />
                      ))}
                    </div>
                  </div>
                </>
              )}
          </div>
        )}

        {/* Current Voice (shown in replace mode) */}
        {isReplaceMode && currentAssignment && (
          <div className="max-w-[calc(50%-0.5rem)] space-y-2">
            <h2 className="text-muted-foreground text-sm font-medium">
              Current Voice
            </h2>
            <VoiceCard
              provider={currentAssignment.provider}
              voiceEntry={currentVoiceEntry || undefined}
              sts_id={currentAssignment.sts_id}
              isCustom={
                !!(currentAssignment.provider && !currentAssignment.sts_id)
              }
              onAssignVoice={() => {}}
              voiceUsageMap={voiceUsageMap}
              currentCharacter={characterName}
            />
          </div>
        )}

        {/* Assignment Mutation Error */}
        {assignVoiceMutation.error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              Failed to assign voice: {assignVoiceMutation.error.message}
            </AlertDescription>
          </Alert>
        )}

        {/* Provider Selection */}
        <div className="space-y-4">
          <h2 className="text-lg font-semibold">Select TTS Provider</h2>

          {isLoading ? (
            <div className="flex h-48 items-center justify-center">
              <Loader2 className="text-muted-foreground h-6 w-6 animate-spin" />
            </div>
          ) : providersError ? (
            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                Failed to load TTS providers: {providersError.message}
              </AlertDescription>
            </Alert>
          ) : voicesError ? (
            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                Failed to load voice library: {voicesError.message}
              </AlertDescription>
            </Alert>
          ) : !providers || providers.length === 0 ? (
            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                No TTS providers available. Please check your configuration.
              </AlertDescription>
            </Alert>
          ) : (
            <Tabs
              value={selectedProvider}
              onValueChange={(value) => {
                setSelectedProvider(value);
                setCustomVoiceConfig({}); // Reset custom config
              }}
            >
              {(() => {
                // Filter to only show stable providers for testing
                const stableProviders = providers.filter(
                  (p) =>
                    p.identifier === 'openai' || p.identifier === 'elevenlabs'
                );
                return (
                  <>
                    <TabsList
                      className="grid w-full"
                      style={{
                        gridTemplateColumns: `repeat(${Math.min(stableProviders.length, 4)}, 1fr)`,
                      }}
                    >
                      {stableProviders.map((provider) => (
                        <TabsTrigger
                          key={provider.identifier}
                          value={provider.identifier}
                        >
                          {provider.name}
                        </TabsTrigger>
                      ))}
                    </TabsList>

                    {stableProviders.map((provider) => (
                      <TabsContent
                        key={provider.identifier}
                        value={provider.identifier}
                        className="space-y-4"
                      >
                        {/* Voice Cards Grid */}
                        {voiceList.length === 0 ? (
                          <Alert>
                            <AlertDescription>
                              No library voices available for this provider.
                            </AlertDescription>
                          </Alert>
                        ) : (
                          <div className="grid gap-4 md:grid-cols-2">
                            {/* Custom Voice Card - Always first */}
                            <CustomVoiceCard
                              provider={selectedProvider}
                              onAssignVoice={handleCustomVoiceAssign}
                              currentConfig={customVoiceConfig}
                            />

                            {/* Library Voice Cards */}
                            {voiceList.map((voice) => (
                              <VoiceCard
                                key={voice.sts_id}
                                provider={selectedProvider}
                                voiceEntry={voice}
                                sts_id={voice.sts_id}
                                onAssignVoice={() =>
                                  handleLibraryVoiceAssign(voice)
                                }
                                showAssignButton={true}
                                voiceUsageMap={voiceUsageMap}
                                currentCharacter={characterName}
                              />
                            ))}
                          </div>
                        )}
                      </TabsContent>
                    ))}
                  </>
                );
              })()}
            </Tabs>
          )}
        </div>

        {/* API Key Warning Dialog */}
        <ApiKeyWarning
          open={showApiKeyWarning}
          onClose={() => setShowApiKeyWarning(false)}
          provider={selectedProvider}
          providerDisplayName={
            providers?.find((p) => p.identifier === selectedProvider)?.name
          }
        />
      </div>
    </TooltipProvider>
  );
}
