import { FolderOpen, Loader2, Play, RotateCcw, Save } from 'lucide-react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { apiService } from '@/services/api';
import { useAudioCommands } from '@/services/AudioService';

import { useUpdateVoice } from '../../hooks/mutations/useVoiceEditorMutations';
import {
  useVoiceDetails,
  useVoiceLibrarySchema,
} from '../../hooks/queries/useVoiceLibrary';
import { useVoiceEditorStore } from '../../stores/voiceEditorStore';
import type { VoiceUpdateRequest } from '../../types/voice-editor';
import { LLMPropertyReasoning } from './LLMPropertyReasoning';
import { VoiceEnumSelector } from './VoiceEnumSelector';
import { VoicePropertySlider } from './VoicePropertySlider';
import { VoiceTagEditor } from './VoiceTagEditor';
import { VoiceTextEditor } from './VoiceTextEditor';

// Form state shape
interface FormState {
  voiceProperties: Record<string, number | string>;
  description: Record<string, string>;
  characterTypes: string[];
  customTags: string[];
}

function buildFormState(
  voiceData: {
    voice_properties?: Record<string, unknown>;
    description?: Record<string, unknown>;
    tags?: Record<string, unknown>;
  } | null
): FormState {
  const vp = voiceData?.voice_properties ?? {};
  const desc = voiceData?.description ?? {};
  const tags = voiceData?.tags ?? {};
  return {
    voiceProperties: {
      age: (vp.age as number) ?? 0.5,
      authority: (vp.authority as number) ?? 0.5,
      energy: (vp.energy as number) ?? 0.5,
      pace: (vp.pace as number) ?? 0.5,
      performative: (vp.performative as number) ?? 0.5,
      pitch: (vp.pitch as number) ?? 0.5,
      quality: (vp.quality as number) ?? 0.5,
      range: (vp.range as number) ?? 0.5,
      accent: (vp.accent as string) ?? '',
      gender: (vp.gender as string) ?? '',
      special_vocal_characteristics:
        (vp.special_vocal_characteristics as string) ?? '',
    },
    description: {
      custom_description: (desc.custom_description as string) ?? '',
      perceived_age: (desc.perceived_age as string) ?? '',
    },
    characterTypes: (tags.character_types as string[]) ?? [],
    customTags: (tags.custom_tags as string[]) ?? [],
  };
}

export function VoiceEditorView() {
  const {
    selectedProvider,
    selectedStsId,
    llmRunData,
    llmRunDir,
    setIsDirty,
    setShowLoadRunDialog,
  } = useVoiceEditorStore();
  const { data: schema, isLoading: schemaLoading } = useVoiceLibrarySchema();
  const { data: voiceDetails, isLoading: voiceLoading } = useVoiceDetails(
    selectedProvider ?? '',
    selectedStsId ?? ''
  );
  const updateVoice = useUpdateVoice();
  const { loadAndPlay, loadWithMetadata, clear } = useAudioCommands();

  // Local form state
  const [formState, setFormState] = useState<FormState>(() =>
    buildFormState(null)
  );

  // The "original" state from the query (source of truth)
  const originalState = useMemo(
    () =>
      voiceDetails
        ? buildFormState({
            voice_properties:
              voiceDetails.voice_properties as unknown as Record<
                string,
                unknown
              >,
            description: voiceDetails.description as unknown as Record<
              string,
              unknown
            >,
            tags: voiceDetails.tags as unknown as Record<string, unknown>,
          })
        : null,
    [voiceDetails]
  );

  // Reset form when voice changes
  useEffect(() => {
    if (originalState) {
      setFormState(originalState);
      setIsDirty(false);
    }
  }, [originalState, setIsDirty]);

  // Check dirty state
  const isDirty = useMemo(() => {
    if (!originalState) return false;
    return JSON.stringify(formState) !== JSON.stringify(originalState);
  }, [formState, originalState]);

  // Sync dirty state to store
  useEffect(() => {
    setIsDirty(isDirty);
  }, [isDirty, setIsDirty]);

  // Load preview when voice selection changes
  const prevVoiceRef = useRef<string | null>(null);
  useEffect(() => {
    if (selectedStsId === prevVoiceRef.current) return;
    if (voiceLoading) {
      // Voice data still loading — clear old playback
      if (prevVoiceRef.current !== null) clear();
      return;
    }
    prevVoiceRef.current = selectedStsId;
    if (voiceDetails?.preview_url && selectedStsId && selectedProvider) {
      loadWithMetadata(voiceDetails.preview_url, {
        primaryText: selectedStsId,
        secondaryText: `${selectedProvider} · Preview`,
      });
    } else {
      clear();
    }
  }, [
    selectedStsId,
    voiceLoading,
    voiceDetails?.preview_url,
    selectedProvider,
    loadWithMetadata,
    clear,
  ]);

  // Update handlers
  const setVoiceProperty = useCallback(
    (key: string, value: number | string) => {
      setFormState((prev) => ({
        ...prev,
        voiceProperties: { ...prev.voiceProperties, [key]: value },
      }));
    },
    []
  );

  const setDescription = useCallback((key: string, value: string) => {
    setFormState((prev) => ({
      ...prev,
      description: { ...prev.description, [key]: value },
    }));
  }, []);

  const setCharacterTypes = useCallback((tags: string[]) => {
    setFormState((prev) => ({ ...prev, characterTypes: tags }));
  }, []);

  const setCustomTags = useCallback((tags: string[]) => {
    setFormState((prev) => ({ ...prev, customTags: tags }));
  }, []);

  // Save handler
  const handleSave = useCallback(() => {
    if (!selectedProvider || !selectedStsId) return;

    const rangeProps: Record<string, number> = {};
    const enumProps: Record<string, string> = {};
    let specialVocal: string | undefined;

    for (const [key, value] of Object.entries(formState.voiceProperties)) {
      if (key === 'special_vocal_characteristics') {
        specialVocal = value as string;
      } else if (typeof value === 'number') {
        rangeProps[key] = value;
      } else if (typeof value === 'string' && value) {
        enumProps[key] = value;
      }
    }

    const updates: VoiceUpdateRequest = {
      voice_properties: {
        ...rangeProps,
        ...enumProps,
        ...(specialVocal !== undefined
          ? { special_vocal_characteristics: specialVocal }
          : {}),
      },
      description: {
        ...(formState.description.custom_description
          ? { custom_description: formState.description.custom_description }
          : {}),
        ...(formState.description.perceived_age
          ? { perceived_age: formState.description.perceived_age }
          : {}),
      },
      tags: {
        ...(formState.characterTypes.length > 0
          ? { character_types: formState.characterTypes }
          : {}),
        ...(formState.customTags.length > 0
          ? { custom_tags: formState.customTags }
          : {}),
      },
    };

    updateVoice.mutate(
      { provider: selectedProvider, stsId: selectedStsId, updates },
      {
        onSuccess: () => {
          setIsDirty(false);
        },
      }
    );
  }, [selectedProvider, selectedStsId, formState, updateVoice, setIsDirty]);

  // Reset handler
  const handleReset = useCallback(() => {
    if (originalState) {
      setFormState(originalState);
    }
  }, [originalState]);

  // Play preview handler
  const handlePlayPreview = useCallback(() => {
    if (!voiceDetails?.preview_url || !selectedProvider || !selectedStsId)
      return;
    loadAndPlay(voiceDetails.preview_url, {
      primaryText: selectedStsId,
      secondaryText: `${selectedProvider} · Preview`,
    });
  }, [voiceDetails?.preview_url, selectedProvider, selectedStsId, loadAndPlay]);

  // Play LLM audio sample
  const handlePlayLLMAudio = useCallback(
    (type: 'neutral' | 'expressive') => {
      if (!llmRunDir || !selectedProvider || !selectedStsId) return;
      const runId = llmRunDir.split('/').pop() ?? '';
      const suffix = type === 'neutral' ? '_neutral' : '_expressive';
      const filename = `${selectedProvider}_${selectedStsId}${suffix}.mp3`;
      const url = apiService.getLLMRunAudioUrl(runId, filename);
      loadAndPlay(url, {
        primaryText: `${selectedStsId} (${type})`,
        secondaryText: `${selectedProvider} · LLM sample`,
      });
    },
    [llmRunDir, selectedProvider, selectedStsId, loadAndPlay]
  );

  // Get LLM data for current voice
  const currentLLMVoice =
    llmRunData && selectedStsId ? llmRunData.voices[selectedStsId] : null;
  const llmReasoning = currentLLMVoice?.result?.reasoning;

  // Parse LLM flags to map property names to their full flag texts
  const flagsByProperty = useMemo(() => {
    if (!currentLLMVoice?.flags?.length) return new Map<string, string[]>();
    const map = new Map<string, string[]>();
    for (const flag of currentLLMVoice.flags) {
      const match = flag.match(/\w+:(\w+)/);
      if (match) {
        const prop = match[1];
        const existing = map.get(prop) ?? [];
        existing.push(flag);
        map.set(prop, existing);
      }
    }
    return map;
  }, [currentLLMVoice]);

  // Categorize schema properties
  const rangeProperties = useMemo(() => {
    if (!schema) return [];
    return Object.entries(schema.voiceProperties).filter(
      ([, def]) => def.type === 'range'
    );
  }, [schema]);

  const enumProperties = useMemo(() => {
    if (!schema) return [];
    return Object.entries(schema.voiceProperties).filter(
      ([, def]) => def.type === 'enum'
    );
  }, [schema]);

  const textProperties = useMemo(() => {
    if (!schema) return [];
    return Object.entries(schema.voiceProperties).filter(
      ([, def]) => def.type === 'text'
    );
  }, [schema]);

  // Empty state
  if (!selectedProvider || !selectedStsId) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="space-y-3 text-center">
          <p className="text-muted-foreground text-sm">
            Select a provider and voice from the panel to begin editing.
          </p>
          <p className="text-muted-foreground text-xs">
            Optional: load an LLM voice labeling run to include evaluations and
            sample audio.
          </p>
          <Button
            size="sm"
            variant="outline"
            className="cursor-pointer"
            onClick={() => setShowLoadRunDialog(true)}
          >
            <FolderOpen className="mr-1.5 size-3" />
            Load LLM Run Data
          </Button>
        </div>
      </div>
    );
  }

  if (schemaLoading || voiceLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="text-muted-foreground size-5 animate-spin" />
      </div>
    );
  }

  return (
    <ScrollArea className="h-full">
      <div className="mx-auto max-w-2xl space-y-6 p-6">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-lg font-semibold">{selectedStsId}</h2>
            <p className="text-muted-foreground text-xs">
              {selectedProvider}
              {voiceDetails?.description?.provider_name &&
                ` \u00B7 ${voiceDetails.description.provider_name}`}
            </p>
            {/* Audio playback links */}
            <div className="mt-1.5 flex items-center gap-2">
              {voiceDetails?.preview_url && (
                <Button
                  size="sm"
                  variant="ghost"
                  className="h-6 cursor-pointer gap-1 px-2 text-[10px]"
                  onClick={handlePlayPreview}
                >
                  <Play className="size-3" />
                  Play Preview
                </Button>
              )}
              {currentLLMVoice && (
                <>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-6 cursor-pointer gap-1 px-2 text-[10px]"
                    onClick={() => handlePlayLLMAudio('neutral')}
                  >
                    <Play className="size-3" />
                    Neutral
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-6 cursor-pointer gap-1 px-2 text-[10px]"
                    onClick={() => handlePlayLLMAudio('expressive')}
                  >
                    <Play className="size-3" />
                    Expressive
                  </Button>
                </>
              )}
            </div>
            {/* Provider description */}
            {voiceDetails?.description?.provider_description && (
              <p className="text-muted-foreground mt-2 max-w-md text-xs">
                {voiceDetails.description.provider_description}
              </p>
            )}
          </div>
          <div className="flex gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={handleReset}
              disabled={!isDirty}
              className="h-8 cursor-pointer text-xs"
            >
              <RotateCcw className="mr-1 size-3" />
              Reset
            </Button>
            <Button
              size="sm"
              onClick={handleSave}
              disabled={!isDirty || updateVoice.isPending}
              className="h-8 cursor-pointer text-xs"
            >
              {updateVoice.isPending ? (
                <Loader2 className="mr-1 size-3 animate-spin" />
              ) : (
                <Save className="mr-1 size-3" />
              )}
              Save
            </Button>
          </div>
        </div>

        {updateVoice.isError && (
          <p className="text-destructive text-xs">
            Save failed: {updateVoice.error.message}
          </p>
        )}

        {/* LLM flags */}
        {currentLLMVoice && (
          <LLMPropertyReasoning voiceData={currentLLMVoice} />
        )}

        {/* Enum properties */}
        <section className="space-y-3">
          <h3 className="text-sm font-medium">Classification</h3>
          <div className="grid grid-cols-2 gap-4">
            {enumProperties.map(([name, def]) => (
              <VoiceEnumSelector
                key={name}
                name={name}
                schema={def}
                value={formState.voiceProperties[name] as string}
                onChange={(v) => setVoiceProperty(name, v)}
              />
            ))}
          </div>
        </section>

        <Separator />

        {/* Range properties */}
        <section className="space-y-3">
          <h3 className="text-sm font-medium">Voice Properties</h3>
          <div className="space-y-4">
            {rangeProperties.map(([name, def]) => (
              <VoicePropertySlider
                key={name}
                name={name}
                schema={def}
                value={formState.voiceProperties[name] as number}
                onChange={(v) => setVoiceProperty(name, v)}
                reasoning={llmReasoning?.[name]}
                warningFlags={flagsByProperty.get(name)}
              />
            ))}
          </div>
        </section>

        <Separator />

        {/* Text properties */}
        <section className="space-y-3">
          <h3 className="text-sm font-medium">Text Fields</h3>
          {textProperties.map(([name, def]) => (
            <VoiceTextEditor
              key={name}
              name={name}
              label={def.description}
              value={(formState.voiceProperties[name] as string) ?? ''}
              onChange={(v) => setVoiceProperty(name, v)}
              placeholder={def.description}
            />
          ))}
          <VoiceTextEditor
            name="custom_description"
            label="Custom Description"
            value={formState.description.custom_description}
            onChange={(v) => setDescription('custom_description', v)}
            placeholder="Description of the voice..."
            rows={3}
          />
          <VoiceTextEditor
            name="perceived_age"
            label="Perceived Age"
            value={formState.description.perceived_age}
            onChange={(v) => setDescription('perceived_age', v)}
            placeholder="e.g., 25-35 years"
          />
        </section>

        <Separator />

        {/* Tags */}
        <section className="space-y-3">
          <h3 className="text-sm font-medium">Tags</h3>
          <VoiceTagEditor
            label="Character Types"
            tags={formState.characterTypes}
            onChange={setCharacterTypes}
          />
          <VoiceTagEditor
            label="Custom Tags"
            tags={formState.customTags}
            onChange={setCustomTags}
          />
        </section>
      </div>
    </ScrollArea>
  );
}
