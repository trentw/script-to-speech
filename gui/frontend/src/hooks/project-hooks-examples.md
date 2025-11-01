# Project Mode TanStack Query Hooks - Usage Examples

This document provides examples of how to use the Project Mode TanStack Query hooks for intelligent caching and CLI/GUI interoperability.

## useProjectStatus Hook

Fetches detailed project status including file existence and metadata:

```typescript
import { useProjectStatus } from '@/hooks/queries';

function ProjectOverview() {
  const store = useAppStore();

  // Only fetch if we're in project mode
  const inputPath = store.mode === 'project' ? store.project.inputPath : undefined;

  const { status, isLoading, error, invalidate, isStale } = useProjectStatus(inputPath);

  if (isLoading) {
    return <ProjectStatusSkeleton />;
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertTitle>Failed to load project</AlertTitle>
        <AlertDescription>
          {error.message}
          <Button onClick={invalidate} variant="link">Retry</Button>
        </AlertDescription>
      </Alert>
    );
  }

  if (!status) {
    return <NoProjectSelected />;
  }

  return (
    <div className="space-y-4">
      {/* Progress indicators */}
      <div className="space-y-3">
        {status.screenplayParsed ? (
          <div className="flex items-center gap-2">
            <CheckCircle className="h-5 w-5 text-green-500" />
            <span>Screenplay parsed ({status.dialogueChunks} chunks)</span>
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <Circle className="h-5 w-5 text-muted-foreground" />
            <span>Parse screenplay</span>
          </div>
        )}

        {status.voicesCast ? (
          <div className="flex items-center gap-2">
            <CheckCircle className="h-5 w-5 text-green-500" />
            <span>Voices cast ({status.voicesAssigned}/{status.speakerCount} speakers)</span>
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <Circle className="h-5 w-5 text-muted-foreground" />
            <span>Cast voices</span>
          </div>
        )}
      </div>

      {/* Error states for corrupt files */}
      {status.jsonError && (
        <Alert variant="warning">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Screenplay JSON Issue</AlertTitle>
          <AlertDescription>
            {status.jsonError}
            <Button variant="link" size="sm" onClick={handleReparse}>
              Re-parse Screenplay
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {/* Manual refresh for CLI changes */}
      {isStale && (
        <Button onClick={invalidate} variant="outline" size="sm">
          Refresh Status
        </Button>
      )}
    </div>
  );
}
```

## useDiscoverProjects Hook

Discovers existing projects in the workspace:

```typescript
import { useDiscoverProjects } from '@/hooks/queries';

function ProjectSelector() {
  const { data: projects, isLoading, error } = useDiscoverProjects({ limit: 10 });

  if (isLoading) {
    return <div>Scanning for projects...</div>;
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          Failed to scan for projects: {error.message}
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-medium">Recent Projects</h3>
      {projects?.length === 0 ? (
        <p className="text-sm text-muted-foreground">No projects found</p>
      ) : (
        <div className="space-y-1">
          {projects?.map((project) => (
            <button
              key={project.inputPath}
              onClick={() => openProject(project)}
              className="w-full text-left p-2 hover:bg-accent rounded-md"
            >
              <div className="font-medium">{project.name}</div>
              <div className="text-xs text-muted-foreground">
                {project.hasJson ? '✓ Parsed' : '○ Not parsed'} •
                {project.hasVoiceConfig ? '✓ Voices' : '○ No voices'} •
                {new Date(project.lastModified).toLocaleDateString()}
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
```

## useCreateProject Hook

Creates new projects from uploaded files:

```typescript
import { useCreateProject } from '@/hooks/mutations';

function NewProjectUpload() {
  const createProject = useCreateProject();
  const store = useAppStore();
  const navigate = useNavigate();

  const handleFileUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return;

    const file = files[0];

    try {
      const result = await createProject.mutateAsync(file);

      // Update store and navigate to project
      store.setProject({
        screenplayName: result.screenplayName,
        inputPath: result.inputPath,
        outputPath: result.outputPath,
      });
      store.addRecentProject(result.inputPath);

      navigate('/project');

      toast.success(`Project "${result.screenplayName}" created successfully!`);
    } catch (error) {
      toast.error(`Failed to create project: ${error.message}`);
    }
  };

  return (
    <div className="space-y-4">
      <div>
        <Label htmlFor="screenplay-file">Upload Screenplay</Label>
        <Input
          id="screenplay-file"
          type="file"
          accept=".pdf,.txt"
          onChange={(e) => handleFileUpload(e.target.files)}
          disabled={createProject.isPending}
        />
      </div>

      {createProject.isPending && (
        <div className="flex items-center gap-2">
          <Loader2 className="h-4 w-4 animate-spin" />
          <span>Creating project and parsing screenplay...</span>
        </div>
      )}

      {createProject.error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            {createProject.error.message}
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
}
```

## CLI/GUI Interoperability Features

### Automatic Refresh on Window Focus

The hooks automatically detect when files change outside the GUI (e.g., via CLI):

```typescript
// This happens automatically when user switches back to GUI window
// after running CLI commands that modify project files

const { status, isStale } = useProjectStatus(inputPath);

// isStale will be true if data was refetched due to window focus
// status will contain the latest data reflecting CLI changes
```

### Manual Cache Invalidation

Use the `invalidate` function after operations that modify project files:

```typescript
function VoiceCastingComponent() {
  const { status, invalidate } = useProjectStatus(inputPath);

  const handleSaveVoiceConfig = async (config: VoiceConfig) => {
    await saveVoiceConfigToFile(config);

    // Manually invalidate cache to reflect changes
    await invalidate();

    toast.success('Voice configuration saved!');
  };

  return (
    <VoiceCastingInterface
      onSave={handleSaveVoiceConfig}
      currentStatus={status}
    />
  );
}
```

### Error Handling Strategy

The hooks implement smart error handling for different scenarios:

```typescript
const { status, error } = useProjectStatus(inputPath);

// Network/server errors - will retry automatically
if (error?.message.includes('fetch')) {
  // Show network error with retry option
}

// Project not found errors - don't retry
if (error?.message.includes('not found')) {
  // Show project missing error with option to select different project
}

// Parse errors in project files - shown in status object
if (status?.jsonError) {
  // Show option to re-parse screenplay
}

if (status?.voiceConfigError) {
  // Show option to fix YAML syntax
}
```

## Performance Considerations

### Cache Configuration

- **Project Status**: 5s stale time, 5min cache time - balances freshness with performance
- **Project Discovery**: 30s stale time, 5min cache time - filesystem scanning is expensive
- **Window Focus Refetching**: Critical for CLI/GUI interop, enabled on all project hooks

### Optimistic Updates

The `useCreateProject` hook pre-populates the cache with optimistic data:

```typescript
// After successful project creation, the status is immediately available
// without an additional API call
const newProject = await createProject.mutateAsync(file);

// This data is already cached and available:
const { status } = useProjectStatus(newProject.inputPath);
// status.screenplayParsed === true (optimistic)
// status.voicesCast === false (realistic)
```

This approach provides an optimal balance of performance, data freshness, and CLI/GUI interoperability for the Project Mode implementation.
