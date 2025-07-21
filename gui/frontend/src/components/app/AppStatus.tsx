export const AppStatus = ({ connected }: { connected: boolean }) => {
  if (connected) {
    return null;
  }

  return (
    <div className="bg-background flex min-h-screen items-center justify-center">
      <div className="text-center">
        <div className="text-destructive mb-4 text-6xl">⚠️</div>
        <h1 className="text-foreground mb-4 text-2xl font-bold">
          Backend Disconnected
        </h1>
        <p className="text-muted-foreground mb-4">
          Cannot connect to the TTS backend server at http://127.0.0.1:8000
        </p>
        <p className="text-muted-foreground text-sm">
          Make sure the backend server is running:{' '}
          <code className="bg-muted rounded px-1 py-0.5">
            cd gui/backend && uv run sts-gui-server
          </code>
        </p>
      </div>
    </div>
  );
};

export const AppLoading = () => (
  <div className="bg-background flex min-h-screen items-center justify-center">
    <div className="text-center">
      <div className="border-primary mx-auto mb-4 h-8 w-8 animate-spin rounded-full border-b-2"></div>
      <p className="text-muted-foreground">Connecting to backend...</p>
    </div>
  </div>
);
