import React from 'react'
import { cn } from '@/lib/utils'

interface ResponsivePanelProps {
  children: React.ReactNode
  title?: string
  className?: string
  panelClassName?: string
}

export function ResponsivePanel({
  children,
  title,
  className,
  panelClassName
}: ResponsivePanelProps) {
  
  return (
    <div
      className={cn(
        "responsive-panel",
        "flex flex-col h-full",
        panelClassName,
        className
      )}
      style={{
        containerType: 'inline-size',
        containerName: 'panel'
      }}
    >
      {title && (
        <header 
          className="flex items-center justify-between p-4 border-b border-border"
        >
          <h2 className="text-lg font-semibold">{title}</h2>
        </header>
      )}
      <div 
        className="flex-1 overflow-y-auto"
      >
        {children}
      </div>
    </div>
  )
}

export default ResponsivePanel