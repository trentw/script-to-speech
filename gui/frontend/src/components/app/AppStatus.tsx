
export const AppStatus = ({ connected }: { connected: boolean }) => {
  if (connected) {
    return null;
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="text-center">
        <div className="text-destructive text-6xl mb-4">⚠️</div>
        <h1 className="text-2xl font-bold text-foreground mb-4">Backend Disconnected</h1>
        <p className="text-muted-foreground mb-4">
          Cannot connect to the TTS backend server at http://127.0.0.1:8000
        </p>
        <p className="text-sm text-muted-foreground">
          Make sure the backend server is running: <code className="bg-muted px-1 py-0.5 rounded">cd gui/backend && uv run sts-gui-server</code>
        </p>
      </div>
    </div>
  );
};

export const AppLoading = () => (
  <div className="min-h-screen flex items-center justify-center bg-background">
    <div className="text-center">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
      <p className="text-muted-foreground">Connecting to backend...</p>
    </div>
  </div>
);
