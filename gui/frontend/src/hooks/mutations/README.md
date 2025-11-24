# Voice Casting Mutation Hooks

This directory contains React Query mutation hooks for managing voice casting sessions. The mutations follow a simplified pattern focused on cache invalidation rather than complex optimistic updates.

## Architecture: Voice Data vs Metadata

The voice casting system separates **voice data** (stored as YAML fields) from **metadata** (stored as YAML comments):

### Voice Data (YAML Fields)

- `provider`: The TTS provider (e.g., 'openai', 'elevenlabs')
- `sts_id`: The voice ID within that provider
- `provider_config`: Optional provider-specific configuration

### Metadata (YAML Comments)

- `casting_notes`: Director's notes about voice selection
- `role`: Character role type (protagonist, antagonist, etc.)
- Line counts and other analysis data

**Important:** The backend uses `ruamel.yaml` which preserves YAML comments during all updates. This means metadata is automatically preserved when modifying voice assignments.

## Available Hooks

### useAssignVoice

Assigns a voice from the library to a character, preserving all metadata.

```typescript
import { useAssignVoice } from '@/hooks/mutations';

const assignVoice = useAssignVoice();

// Usage - Only voice data is sent
assignVoice.mutate({
  sessionId: 'session-123',
  character: 'ALICE',
  assignment: {
    character: 'ALICE',
    provider: 'openai',
    sts_id: 'alloy',
    provider_config: { speed: 1.0 }, // optional
  },
  versionId: currentVersionId,
});
```

**Behavior:**

- Updates voice fields (provider, sts_id, provider_config)
- Preserves all YAML comments (metadata)
- Uses simple cache invalidation (no optimistic updates)

### useClearVoice

Clears voice assignment from a character while preserving metadata.

```typescript
import { useClearVoice } from '@/hooks/mutations';

const clearVoice = useClearVoice();

// Usage - Removes voice but keeps metadata
clearVoice.mutate({
  sessionId: 'session-123',
  character: 'ALICE',
  versionId: currentVersionId,
});
```

**Behavior:**

- Clears voice fields (sets provider and sts_id to empty strings)
- Preserves all YAML comments (casting notes, role, etc.)
- Character entry remains in YAML with metadata intact

### useUpdateSessionYaml

Updates the entire session YAML content with optimistic updates.

```typescript
import { useUpdateSessionYaml } from '@/hooks/mutations';

const updateYaml = useUpdateSessionYaml();

// Usage - Direct YAML editing
updateYaml.mutate({
  sessionId: 'session-123',
  yamlContent: newYamlContent,
  versionId: currentVersionId,
});
```

**Behavior:**

- Replaces entire YAML content
- Uses optimistic updates for immediate UI feedback
- Automatically rolls back on error
- This is the only mutation with optimistic updates

## Design Principles

### 1. YAML as Single Source of Truth

The YAML file is the authoritative source for all voice casting data. The frontend never parses or modifies YAML directly - all operations go through the backend API.

### 2. Simplified Cache Management

Most mutations use simple cache invalidation rather than optimistic updates:

- Reduces complexity and potential for bugs
- Ensures queries re-run their transformation logic
- Maintains consistency with backend state

### 3. Metadata Preservation

All voice operations preserve metadata through the backend's YAML comment handling:

- The backend skips metadata fields when updating assignments
- `ruamel.yaml` preserves YAML comments and formatting
- Metadata can only be modified through direct YAML editing

### 4. Clear Naming Conventions

- `useAssignVoice`: Sets voice data (from library)
- `useClearVoice`: Removes voice data (preserves metadata)
- `useUpdateSessionYaml`: Direct YAML manipulation

## Version Conflict Handling

All mutations handle concurrent modification conflicts:

- Each mutation requires a `versionId` parameter
- Backend returns 409 status on version mismatch
- User-friendly error messages guide resolution

## Error Handling

```typescript
// All mutations follow this pattern
try {
  await mutation.mutateAsync(data);
} catch (error) {
  if (error.message.includes('version')) {
    // Version conflict - user needs to refresh
  } else {
    // Other errors (network, validation, etc.)
  }
}
```

## Integration Example

```typescript
import {
  useVoiceCastingSession,
  useAssignVoice,
  useClearVoice
} from '@/hooks';

function CharacterCard({ sessionId, character }: Props) {
  const { data: session } = useVoiceCastingSession(sessionId);
  const assignVoice = useAssignVoice();
  const clearVoice = useClearVoice();

  const handleAssignVoice = (voiceData: VoiceData) => {
    if (!session?.yaml_version_id) return;

    assignVoice.mutate({
      sessionId,
      character: character.name,
      assignment: {
        character: character.name,
        provider: voiceData.provider,
        sts_id: voiceData.sts_id
      },
      versionId: session.yaml_version_id
    });
  };

  const handleClearVoice = () => {
    if (!session?.yaml_version_id) return;

    clearVoice.mutate({
      sessionId,
      character: character.name,
      versionId: session.yaml_version_id
    });
  };

  return (
    <div>
      {/* Character UI with voice controls */}
    </div>
  );
}
```

## Query Keys

Consistent query keys for cache management:

- Session data: `['session', sessionId]`
- Sessions list: `['voice-casting-sessions']`
- Parsed YAML: `['parseYaml']` (invalidated by YAML updates)
