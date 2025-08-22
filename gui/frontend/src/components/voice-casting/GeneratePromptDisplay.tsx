import { CheckCircle2, Copy, Download, Loader2 } from 'lucide-react';
import { useState } from 'react';

import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { downloadText } from '@/utils/downloadService';

interface GeneratePromptDisplayProps {
  promptText: string;
  isGenerating: boolean;
  onGenerate: () => void;
  generateButtonText?: string;
  filePrefix: string; // For download filename like "character-notes-prompt" or "voice-library-prompt"
  sessionId: string;
}

export function GeneratePromptDisplay({
  promptText,
  isGenerating,
  onGenerate,
  generateButtonText = 'Generate Prompt',
  filePrefix,
  sessionId,
}: GeneratePromptDisplayProps) {
  const [copiedPrompt, setCopiedPrompt] = useState(false);

  const handleCopyPrompt = () => {
    navigator.clipboard.writeText(promptText);
    setCopiedPrompt(true);
    setTimeout(() => setCopiedPrompt(false), 2000);
  };

  const handleDownloadPrompt = async () => {
    const filename = `${filePrefix}-${sessionId}.txt`;
    await downloadText(promptText, filename, 'text/plain');
  };

  if (isGenerating) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-6 w-6 animate-spin" />
      </div>
    );
  }

  if (promptText) {
    return (
      <div className="space-y-3">
        <Textarea
          value={promptText}
          readOnly
          className="h-48 font-mono text-sm"
        />
        <div className="flex gap-2">
          <Button size="sm" variant="outline" onClick={handleCopyPrompt}>
            {copiedPrompt ? (
              <>
                <CheckCircle2 className="mr-2 h-4 w-4" />
                Copied!
              </>
            ) : (
              <>
                <Copy className="mr-2 h-4 w-4" />
                Copy
              </>
            )}
          </Button>
          <Button size="sm" variant="outline" onClick={handleDownloadPrompt}>
            <Download className="mr-2 h-4 w-4" />
            Download
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="py-8 text-center">
      <Button onClick={onGenerate}>{generateButtonText}</Button>
    </div>
  );
}
