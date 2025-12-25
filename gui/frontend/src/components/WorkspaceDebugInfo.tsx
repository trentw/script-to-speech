import { useQuery } from '@tanstack/react-query';

import { Button } from '@/components/ui/button';
import { API_BASE_URL } from '@/config/api';

interface WorkspaceInfo {
  workspace_dir: string;
  exists: boolean;
  is_production: boolean;
  detection_method: string;
  sys_argv: string[];
  production_flag_present: boolean;
  sys_frozen: boolean | null;
  sys_meipass: string | null;
  sys_platform: string;
}

export function WorkspaceDebugInfo() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['workspace'],
    queryFn: async () => {
      const response = await fetch(`${API_BASE_URL}/workspace`);
      if (!response.ok) throw new Error('Failed to fetch workspace info');
      return response.json() as Promise<WorkspaceInfo>;
    },
    refetchInterval: 5000, // Refresh every 5 seconds
  });

  if (isLoading) {
    return (
      <div className="text-muted-foreground text-sm">
        Loading workspace info...
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-destructive text-sm">
        Failed to load workspace info
      </div>
    );
  }

  if (!data) {
    return null;
  }

  return (
    <div className="space-y-1 font-mono text-xs">
      {/* Primary Status */}
      <div className="flex items-center gap-2">
        <span className="text-muted-foreground">Mode:</span>
        <span
          className={
            data.is_production
              ? 'font-bold text-green-600'
              : 'font-bold text-yellow-600'
          }
        >
          {data.is_production ? 'PRODUCTION' : 'DEVELOPMENT'}
        </span>
      </div>

      {/* Workspace Path */}
      <div className="flex items-center gap-2">
        <span className="text-muted-foreground">Workspace:</span>
        <span
          className="max-w-[200px] truncate font-semibold"
          title={data.workspace_dir || ''}
        >
          {data.workspace_dir || 'unknown'}
        </span>
      </div>

      {/* Production Flag Detection */}
      {data.production_flag_present !== undefined && (
        <div className="flex items-center gap-2">
          <span className="text-muted-foreground">--production flag:</span>
          <span
            className={
              data.production_flag_present ? 'text-green-600' : 'text-red-600'
            }
          >
            {data.production_flag_present ? '✓ present' : '✗ missing'}
          </span>
        </div>
      )}

      {/* Command Line Arguments */}
      {data.sys_argv && data.sys_argv.length > 0 && (
        <div className="mt-2 flex flex-col gap-1">
          <span className="text-muted-foreground">sys.argv:</span>
          <div className="space-y-0.5 pl-2">
            {data.sys_argv.map((arg, idx) => (
              <div key={idx} className="flex items-center gap-1">
                <span className="text-muted-foreground">[{idx}]</span>
                <span
                  className={
                    arg === '--production' ? 'font-bold text-green-600' : ''
                  }
                >
                  {arg}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* PyInstaller State (for comparison) */}
      <div className="border-border mt-2 flex items-center gap-2 border-t pt-2">
        <span className="text-muted-foreground">sys.frozen:</span>
        <span>{String(data.sys_frozen ?? 'undefined')}</span>
      </div>
      <div className="flex items-center gap-2">
        <span className="text-muted-foreground">sys._MEIPASS:</span>
        <span
          className="max-w-[200px] truncate"
          title={data.sys_meipass ?? 'undefined'}
        >
          {data.sys_meipass ?? 'undefined'}
        </span>
      </div>
      <div className="flex items-center gap-2">
        <span className="text-muted-foreground">platform:</span>
        <span>{data.sys_platform}</span>
      </div>

      {/* Clear Local Storage Button */}
      <div className="border-border mt-4 border-t pt-4">
        <Button
          variant="outline"
          size="sm"
          className="text-destructive hover:bg-destructive hover:text-destructive-foreground w-full"
          onClick={() => {
            if (
              confirm(
                'Clear all local storage? This will reset your preferences and reload the app.'
              )
            ) {
              localStorage.removeItem('app-store');
              window.location.reload();
            }
          }}
        >
          Clear Local Storage
        </Button>
      </div>
    </div>
  );
}
