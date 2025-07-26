import { useNavigate } from '@tanstack/react-router'
import { FileText, Library,Wand2 } from 'lucide-react'
import React from 'react'

import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { useVoiceCasting } from '@/stores/appStore'

interface LLMWorkflowButtonsProps {
  sessionId: string
}

export function LLMWorkflowButtons({ sessionId }: LLMWorkflowButtonsProps) {
  const navigate = useNavigate()
  const { castingMethod } = useVoiceCasting()
  
  if (castingMethod !== 'llm-assisted') {
    return null
  }

  return (
    <div className="space-y-4">
      <Separator />
      <div>
        <h3 className="text-lg font-semibold mb-2">LLM-Assisted Workflow</h3>
        <p className="text-sm text-muted-foreground mb-4">
          Use AI to help generate character descriptions and suggest voice assignments
        </p>
        <div className="flex gap-3">
          <Button
            variant="outline"
            onClick={() => navigate({ to: '/voice-casting/$sessionId/notes', params: { sessionId } })}
          >
            <FileText className="mr-2 h-4 w-4" />
            Generate Character Notes
          </Button>
          <Button
            variant="outline"
            onClick={() => navigate({ to: '/voice-casting/$sessionId/library', params: { sessionId } })}
          >
            <Library className="mr-2 h-4 w-4" />
            Voice Library Casting
          </Button>
        </div>
      </div>
    </div>
  )
}