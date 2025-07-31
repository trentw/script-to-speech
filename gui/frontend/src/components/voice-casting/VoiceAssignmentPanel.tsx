import {
  AlertCircle,
  ArrowLeft,
  Hash,
  Loader2,
  MessageSquare,
} from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { TooltipProvider } from '@/components/ui/tooltip';
import { useProviders, useVoiceLibrary } from '@/hooks/queries';
import { useAudioCommands } from '@/hooks/useAudioCommands';
import { useVoiceCasting } from '@/stores/appStore';
import type { VoiceEntry } from '@/types';
import { calculateVoiceUsage } from '@/utils/voiceUsageHelper';

import { CustomVoiceCard } from './CustomVoiceCard';
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
  assignedVoice: {
    provider: string;
    voiceName: string;
    voiceId: string;
  } | null;
}

interface VoiceAssignmentPanelProps {
  characterName: string;
  character: CharacterData;
  onBack: () => void;
  onAssign: () => void;
}

export function VoiceAssignmentPanel({
  characterName,
  character,
  onBack,
  onAssign,
}: VoiceAssignmentPanelProps) {
  // Use real data from hooks
  const {
    data: providers,
    isPending: providersLoading,
    error: providersError,
  } = useProviders();

  const { setCharacterVoice, assignments, screenplayData } = useVoiceCasting();
  const { playVoicePreview } = useAudioCommands();

  // Get current assignment if exists
  const currentAssignment = assignments.get(characterName);

  // Calculate voice usage map
  const voiceUsageMap = useMemo(() => {
    return calculateVoiceUsage(
      assignments,
      screenplayData?.characters,
      characterName
    );
  }, [assignments, screenplayData?.characters, characterName]);

  // Initialize state with current assignment or stable provider default
  const [selectedProvider, setSelectedProvider] = useState<string>(
    currentAssignment?.provider || 'openai'
  );

  const [customVoiceConfig, setCustomVoiceConfig] = useState<
    Record<string, unknown>
  >(currentAssignment?.provider_config || {});

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

  // Load voices for the selected provider
  const {
    data: providerVoices,
    isPending: voicesLoading,
    error: voicesError,
  } = useVoiceLibrary(selectedProvider);

  // Use the voices directly from the hook
  const voiceList = useMemo(() => providerVoices || [], [providerVoices]);

  const handleLibraryVoiceAssign = (voice: VoiceEntry) => {
    setCharacterVoice(characterName, {
      sts_id: voice.sts_id,
      provider: selectedProvider,
      voiceEntry: voice,
    });
    onAssign();
  };

  const handleCustomVoiceAssign = (config: Record<string, unknown>) => {
    setCharacterVoice(characterName, {
      provider: selectedProvider,
      provider_config: config,
    });
    onAssign();
  };

  const handlePlayPreview = async (voice: VoiceEntry) => {
    const providerInfo = providers?.find(
      (p) => p.identifier === selectedProvider
    );
    if (!providerInfo) {
      return;
    }

    await playVoicePreview(voice, providerInfo.name, character.displayName);
  };

  const isLoading = providersLoading || voicesLoading;

  return (
    <TooltipProvider>
      <div className="container mx-auto max-w-4xl space-y-6 p-6">
        {/* Header */}
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={onBack}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div className="flex-1">
            <h1 className="text-2xl font-bold">
              {character.displayName}: Assign Voice
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
        {(character.role || character.castingNotes) && (
          <div className="bg-muted/50 space-y-1 rounded-md p-2">
            {character.role && (
              <p className="text-sm">
                <span className="text-muted-foreground">Role:</span>{' '}
                <span className="font-medium">{character.role}</span>
              </p>
            )}
            {character.castingNotes && (
              <p className="text-muted-foreground text-sm">
                {character.castingNotes}
              </p>
            )}
          </div>
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
                          <div className="grid grid-cols-2 gap-3">
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
                                onAssignVoice={() =>
                                  handleLibraryVoiceAssign(voice)
                                }
                                onPlayPreview={() => handlePlayPreview(voice)}
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
      </div>
    </TooltipProvider>
  );
}
