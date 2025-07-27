import { AlertCircle,ArrowLeft, Check, Loader2, Play } from 'lucide-react';
import { useEffect,useMemo, useState } from 'react';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { appButtonVariants } from '@/components/ui/button-variants';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useProviders, useVoiceLibrary } from '@/hooks/queries';
import { useAudioCommands } from '@/hooks/useAudioCommands';
import { useVoiceCasting } from '@/stores/appStore';
import type { VoiceEntry } from '@/types';

interface CharacterData {
  name: string;
  displayName: string;
  lineCount: number;
  totalCharacters: number;
  longestDialogue: number;
  isNarrator: boolean;
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
  const { data: providers, isPending: providersLoading, error: providersError } = useProviders();
  
  // Debug logging
  console.log('VoiceAssignmentPanel render:', {
    providers,
    providersLoading,
    providersError,
    providersLength: providers?.length
  });
  const { setCharacterAssignment, assignments } = useVoiceCasting();
  const { playVoicePreview } = useAudioCommands();

  // Get current assignment if exists
  const currentAssignment = assignments.get(characterName);
  
  // Initialize state with current assignment or stable provider default
  const [selectedProvider, setSelectedProvider] = useState<string>(
    currentAssignment?.provider || 'openai'
  );
  const [selectedVoice, setSelectedVoice] = useState<string | null>(
    currentAssignment?.voiceId || null
  );

  // Update selected provider when providers load, preferring stable providers
  useEffect(() => {
    if (providers && providers.length > 0 && !currentAssignment?.provider) {
      // Only use openai or elevenlabs as they are stable
      const stableProvider = providers.find(p => p.identifier === 'openai') || 
                            providers.find(p => p.identifier === 'elevenlabs');
      if (stableProvider) {
        setSelectedProvider(stableProvider.identifier);
      }
    }
  }, [providers, currentAssignment?.provider]);

  // Load voices for the selected provider
  const { data: providerVoices, isPending: voicesLoading, error: voicesError } = useVoiceLibrary(selectedProvider);

  // Use the voices directly from the hook
  const voiceList = providerVoices || [];

  // Group voices by gender for better organization
  const voicesByGender = useMemo(() => {
    const grouped: Record<string, VoiceEntry[]> = {
      male: [],
      female: [],
      neutral: [],
      unknown: [],
    };
    
    voiceList.forEach(voice => {
      const gender = voice.voice_properties?.gender?.toLowerCase() || 'unknown';
      if (grouped[gender]) {
        grouped[gender].push(voice);
      } else {
        grouped.unknown.push(voice);
      }
    });
    
    return grouped;
  }, [voiceList]);

  const handleAssign = () => {
    if (selectedVoice && selectedProvider) {
      const voice = voiceList.find(v => v.sts_id === selectedVoice);
      if (voice) {
        setCharacterAssignment(characterName, {
          voiceId: selectedVoice,
          provider: selectedProvider,
          voiceEntry: voice,
          confidence: 1.0,
          reasoning: 'Manually assigned',
        });
        onAssign();
      }
    }
  };

  const handlePlayPreview = async (voice: VoiceEntry) => {
    console.log('handlePlayPreview called:', { voice, selectedProvider, providers });
    console.log('voice.preview_url:', voice.preview_url);
    
    const providerInfo = providers?.find(p => p.identifier === selectedProvider);
    if (!providerInfo) {
      console.log('No provider info found for:', selectedProvider);
      return;
    }
    
    console.log('Calling playVoicePreview with:', {
      voiceId: voice.sts_id,
      providerName: providerInfo.name,
      characterName: character.displayName,
      previewUrl: voice.preview_url
    });
    
    await playVoicePreview(voice, providerInfo.name, character.displayName);
  };

  const isLoading = providersLoading || voicesLoading;

  return (
    <div className="container max-w-4xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={onBack}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div className="flex-1">
          <h1 className="text-2xl font-bold">Assign Voice to {character.displayName}</h1>
          <p className="text-muted-foreground">
            {character.lineCount} lines • {character.totalCharacters.toLocaleString()} characters
          </p>
        </div>
      </div>

      {/* Character Context */}
      <Card>
        <CardHeader>
          <CardTitle>Character Information</CardTitle>
          <CardDescription>
            Consider these details when selecting a voice
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div>
              <p className="text-muted-foreground">Role Type</p>
              <p className="font-medium">
                {character.isNarrator ? 'Narrator / Stage Directions' : 'Speaking Character'}
              </p>
            </div>
            <div>
              <p className="text-muted-foreground">Dialogue Volume</p>
              <p className="font-medium">{character.lineCount} lines</p>
            </div>
            <div>
              <p className="text-muted-foreground">Longest Dialogue</p>
              <p className="font-medium">{character.longestDialogue} characters</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Provider Selection */}
      <div className="space-y-4">
        <h2 className="text-lg font-semibold">Select TTS Provider</h2>
        
        {isLoading ? (
          <div className="flex items-center justify-center h-48">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
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
          <Tabs value={selectedProvider} onValueChange={(value) => {
            setSelectedProvider(value);
            setSelectedVoice(null); // Reset voice selection when provider changes
          }}>
            {(() => {
              // Filter to only show stable providers for testing
              const stableProviders = providers.filter(p => 
                p.identifier === 'openai' || p.identifier === 'elevenlabs'
              );
              return (
                <>
                  <TabsList className="grid w-full" style={{ gridTemplateColumns: `repeat(${Math.min(stableProviders.length, 4)}, 1fr)` }}>
                    {stableProviders.map(provider => (
                      <TabsTrigger key={provider.identifier} value={provider.identifier}>
                        {provider.name}
                      </TabsTrigger>
                    ))}
                  </TabsList>

                  {stableProviders.map(provider => (
                    <TabsContent key={provider.identifier} value={provider.identifier} className="space-y-4">
                      <div className="text-sm text-muted-foreground">
                        {voiceList.length} voices available
                      </div>

                      {voiceList.length === 0 ? (
                        <Alert>
                          <AlertDescription>
                            No voices available for this provider.
                          </AlertDescription>
                        </Alert>
                      ) : (
                        <div className="space-y-4">
                          {Object.entries(voicesByGender).map(([gender, voices]) => {
                            if (voices.length === 0) return null;
                            
                            return (
                              <div key={gender} className="space-y-2">
                                <h3 className="text-sm font-medium capitalize text-muted-foreground">
                                  {gender} Voices ({voices.length})
                                </h3>
                                <div className="grid gap-3">
                                  {voices.map(voice => (
                                    <Card
                                      key={voice.sts_id}
                                      className={`group cursor-pointer transition-all ${
                                        selectedVoice === voice.sts_id
                                          ? 'border-primary ring-2 ring-primary/20'
                                          : 'hover:bg-accent'
                                      }`}
                                      onClick={() => setSelectedVoice(voice.sts_id)}
                                    >
                                      <CardContent className="p-4">
                                        <div className="flex items-center justify-between">
                                          <div className="flex items-center gap-3">
                                            <div className="space-y-1">
                                              <div className="flex items-center gap-2">
                                                <h4 className="font-medium">
                                                  {voice.description?.provider_name || voice.sts_id}
                                                </h4>
                                                {selectedVoice === voice.sts_id && (
                                                  <Check className="h-4 w-4 text-primary" />
                                                )}
                                              </div>
                                              <div className="flex items-center gap-2 flex-wrap">
                                                {voice.voice_properties?.accent && (
                                                  <Badge variant="secondary" className="text-xs">
                                                    {voice.voice_properties.accent}
                                                  </Badge>
                                                )}
                                                {voice.voice_properties?.age && (
                                                  <Badge variant="outline" className="text-xs">
                                                    Age: {voice.voice_properties.age}
                                                  </Badge>
                                                )}
                                                {voice.tags?.character_types?.map(tag => (
                                                  <Badge key={tag} variant="outline" className="text-xs">
                                                    {tag}
                                                  </Badge>
                                                ))}
                                              </div>
                                              {voice.description?.provider_description && (
                                                <p className="text-xs text-muted-foreground line-clamp-2">
                                                  {voice.description.provider_description}
                                                </p>
                                              )}
                                            </div>
                                          </div>
                                          {voice.preview_url && (
                                            <button
                                              className={`${appButtonVariants({ variant: 'list-action', size: 'icon-sm' })} opacity-0 transition-all duration-200 group-hover:opacity-100`}
                                              onClick={(e) => {
                                                e.stopPropagation();
                                                handlePlayPreview(voice);
                                              }}
                                            >
                                              <Play className="h-4 w-4" />
                                            </button>
                                          )}
                                        </div>
                                      </CardContent>
                                    </Card>
                                  ))}
                                </div>
                              </div>
                            );
                          })}
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

      {/* Actions */}
      <Separator />
      <div className="flex items-center justify-between">
        <Button variant="outline" onClick={onBack}>
          Cancel
        </Button>
        <Button onClick={handleAssign} disabled={!selectedVoice}>
          Assign Voice
        </Button>
      </div>
    </div>
  );
}