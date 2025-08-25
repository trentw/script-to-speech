import { useNavigate } from '@tanstack/react-router';
import { MousePointer, Wand2 } from 'lucide-react';
import React from 'react';
import { useState } from 'react';

import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
} from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { interactiveCardVariants } from '@/components/ui/interactive.variants';
import { Label } from '@/components/ui/label';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { cn } from '@/lib/utils';

interface CastingMethodSelectorProps {
  sessionId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CastingMethodSelector({
  sessionId,
  open,
  onOpenChange,
}: CastingMethodSelectorProps) {
  const navigate = useNavigate();

  // Local state for casting method selection
  const [castingMethod, setCastingMethod] = useState<'manual' | 'llm-assisted'>(
    'manual'
  );

  const handleContinue = () => {
    if (castingMethod === 'llm-assisted') {
      navigate({
        to: '/voice-casting/$sessionId/notes',
        params: { sessionId },
      });
    } else {
      // For manual assignment, navigate to main voice casting page
      navigate({ to: '/voice-casting/$sessionId', params: { sessionId } });
    }
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="border bg-white shadow-lg sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>Choose Voice Casting Method</DialogTitle>
          <DialogDescription>
            Select how you'd like to assign voices to your characters
          </DialogDescription>
        </DialogHeader>

        <RadioGroup
          value={castingMethod}
          onValueChange={(value: 'manual' | 'llm-assisted') =>
            setCastingMethod(value)
          }
        >
          <div className="space-y-4">
            <Card
              className={cn(
                interactiveCardVariants({ variant: 'action' }),
                castingMethod === 'manual' && 'border-primary bg-accent'
              )}
              onClick={() => setCastingMethod('manual')}
            >
              <CardHeader className="space-y-1">
                <div className="flex items-center space-x-2">
                  <RadioGroupItem
                    value="manual"
                    id="manual"
                    onClick={(e) => e.stopPropagation()}
                  />
                  <Label
                    htmlFor="manual"
                    className="flex cursor-pointer items-center gap-2"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <MousePointer className="h-4 w-4" />
                    <span className="font-semibold">Manual Assignment</span>
                  </Label>
                </div>
              </CardHeader>
              <CardContent>
                <CardDescription>
                  Manually browse and select voices for each character using the
                  voice library. You have full control over every assignment.
                </CardDescription>
              </CardContent>
            </Card>

            <Card
              className={cn(
                interactiveCardVariants({ variant: 'action' }),
                castingMethod === 'llm-assisted' && 'border-primary bg-accent'
              )}
              onClick={() => setCastingMethod('llm-assisted')}
            >
              <CardHeader className="space-y-1">
                <div className="flex items-center space-x-2">
                  <RadioGroupItem
                    value="llm-assisted"
                    id="llm-assisted"
                    onClick={(e) => e.stopPropagation()}
                  />
                  <Label
                    htmlFor="llm-assisted"
                    className="flex cursor-pointer items-center gap-2"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <Wand2 className="h-4 w-4" />
                    <span className="font-semibold">LLM-Assisted</span>
                  </Label>
                </div>
              </CardHeader>
              <CardContent>
                <CardDescription>
                  Use an AI language model to help generate character
                  descriptions and suggest voice assignments based on your
                  screenplay content and available voices.
                </CardDescription>
              </CardContent>
            </Card>
          </div>
        </RadioGroup>

        <div className="mt-6 flex justify-end gap-3">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleContinue}>Continue</Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
