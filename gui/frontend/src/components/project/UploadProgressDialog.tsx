import { useNavigate } from '@tanstack/react-router';
import { AlertTriangle, CheckCircle2, Loader2 } from 'lucide-react';

import { appButtonVariants } from '@/components/ui/button-variants';
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { useProject, useUploadDialog } from '@/stores/appStore';

/**
 * Global upload progress dialog that shows screenplay parsing status.
 * Rendered at the root level so it can be triggered from any component.
 */
export function UploadProgressDialog() {
  const navigate = useNavigate();
  const { setProject, addRecentProject } = useProject();
  const { uploadDialog, resetUploadDialog } = useUploadDialog();

  const handleContinueToProject = () => {
    if (
      uploadDialog.status === 'complete' ||
      uploadDialog.status === 'detection'
    ) {
      setProject(uploadDialog.projectMeta);
      addRecentProject(uploadDialog.projectMeta.inputPath);
      resetUploadDialog();
      navigate({ to: '/project' });
    }
  };

  const handleConfigureParsing = () => {
    if (uploadDialog.status === 'detection') {
      setProject(uploadDialog.projectMeta);
      addRecentProject(uploadDialog.projectMeta.inputPath);
      resetUploadDialog();
      navigate({ to: '/project/screenplay/configure' });
    }
  };

  return (
    <Dialog
      open={uploadDialog.status !== 'idle'}
      onOpenChange={(open) => {
        // Only allow closing when not processing
        if (!open && uploadDialog.status !== 'processing') {
          resetUploadDialog();
        }
      }}
    >
      <DialogContent className="sm:max-w-xl">
        {/* Processing State */}
        {uploadDialog.status === 'processing' && (
          <>
            <DialogHeader>
              <DialogTitle>Processing Screenplay</DialogTitle>
            </DialogHeader>
            <div className="flex items-center gap-3 py-6">
              <Loader2 className="text-primary h-5 w-5 animate-spin" />
              <span className="text-muted-foreground">
                {uploadDialog.step === 'parsing'
                  ? 'Parsing screenplay...'
                  : 'Checking for headers/footers...'}
              </span>
            </div>
          </>
        )}

        {/* Complete/Detection States - unified structure */}
        {(uploadDialog.status === 'complete' ||
          uploadDialog.status === 'detection') && (
          <>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <CheckCircle2 className="h-5 w-5 text-green-500" />
                Screenplay Processing Complete
              </DialogTitle>
            </DialogHeader>

            <div className="space-y-4 py-4">
              {/* Success info with bold values */}
              <p className="text-muted-foreground">
                Your screenplay has been processed into{' '}
                <span className="text-foreground font-semibold">
                  {uploadDialog.dialogueChunks}
                </span>{' '}
                dialogue chunks with{' '}
                <span className="text-foreground font-semibold">
                  {uploadDialog.speakerCount}
                </span>{' '}
                unique speakers. You can review details in Screenplay Info.
              </p>

              {/* Detection warning section - only if detection status */}
              {uploadDialog.status === 'detection' && (
                <div className="space-y-3 rounded-lg border border-amber-200 bg-amber-50 p-4">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4 text-amber-600" />
                    <span className="font-medium text-amber-800">
                      Headers/Footers Detected
                    </span>
                  </div>

                  <p className="text-sm text-amber-700">
                    Some repeating patterns were found during parsing.
                  </p>

                  {/* Auto-removed patterns - show actual texts */}
                  {uploadDialog.autoRemoved.length > 0 && (
                    <div className="space-y-1">
                      <p className="text-xs font-medium text-green-700">
                        Automatically removed ({uploadDialog.autoRemoved.length}
                        ):
                      </p>
                      <ul className="space-y-1">
                        {uploadDialog.autoRemoved.slice(0, 3).map((p) => (
                          <li key={p.text} className="text-xs">
                            <span className="block truncate font-mono text-amber-800">
                              {p.text}
                            </span>
                            <span className="text-amber-600">
                              {Math.round(p.occurrencePercentage)}% (
                              {p.occurrenceCount} of {p.totalPages} pages)
                            </span>
                          </li>
                        ))}
                        {uploadDialog.autoRemoved.length > 3 && (
                          <li className="text-xs text-amber-600">
                            +{uploadDialog.autoRemoved.length - 3} more
                          </li>
                        )}
                      </ul>
                    </div>
                  )}

                  {/* Suggested patterns - show actual texts */}
                  {uploadDialog.suggested.length > 0 && (
                    <div className="space-y-1">
                      <p className="text-xs font-medium text-amber-700">
                        Suggested for review ({uploadDialog.suggested.length}):
                      </p>
                      <ul className="space-y-1">
                        {uploadDialog.suggested.slice(0, 3).map((p) => (
                          <li key={p.text} className="text-xs">
                            <span className="block truncate font-mono text-amber-800">
                              {p.text}
                            </span>
                            <span className="text-amber-600">
                              {Math.round(p.occurrencePercentage)}% (
                              {p.occurrenceCount} of {p.totalPages} pages)
                            </span>
                          </li>
                        ))}
                        {uploadDialog.suggested.length > 3 && (
                          <li className="text-xs text-amber-600">
                            +{uploadDialog.suggested.length - 3} more
                          </li>
                        )}
                      </ul>
                    </div>
                  )}

                  <p className="text-xs text-amber-600">
                    To adjust these settings, use the Configure Parsing button
                    under Screenplay Info, or click the button below.
                  </p>
                </div>
              )}
            </div>

            <DialogFooter className="flex-col gap-2 sm:flex-row">
              {uploadDialog.status === 'detection' && (
                <button
                  onClick={handleConfigureParsing}
                  className={appButtonVariants({ variant: 'secondary' })}
                >
                  Configure Parsing
                </button>
              )}
              <button
                onClick={handleContinueToProject}
                className={appButtonVariants({ variant: 'primary' })}
              >
                Continue to Project
              </button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
