import React from 'react'
import { motion } from 'framer-motion'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { 
  Mic, 
  PanelLeftClose,
  PanelLeftOpen
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useViewportSize } from '@/hooks/useViewportSize'

interface NavigationItem {
  id: string
  label: string
  icon: React.ComponentType<{ className?: string }>
  onClick?: () => void
  isActive?: boolean
}

interface AdaptiveNavigationProps {
  items?: NavigationItem[]
  isExpanded?: boolean
  onToggleExpanded?: () => void
  className?: string
}

const defaultItems: NavigationItem[] = [
  {
    id: 'tts',
    label: 'Text to Speech',
    icon: Mic,
    isActive: true
  }
]

export function AdaptiveNavigation({
  items = defaultItems,
  isExpanded = true,
  onToggleExpanded,
  className
}: AdaptiveNavigationProps) {
  const { isMobile, isTablet } = useViewportSize()

  return (
    <>
      {/* Mobile/Tablet Overlay */}
      {(isMobile || isTablet) && isExpanded && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 bg-black/80 backdrop-blur-sm z-40"
          onClick={onToggleExpanded}
        />
      )}
      
      {/* Desktop/Tablet Navigation */}
      <motion.nav
        key={`nav-${isMobile ? 'mobile' : isTablet ? 'tablet' : 'desktop'}`}
        initial={
          (isMobile || isTablet) 
            ? { x: -256 } 
            : { width: isExpanded ? 256 : 64 }
        }
        animate={
          (isMobile || isTablet) 
            ? { x: isExpanded ? 0 : -256 } 
            : { width: isExpanded ? 256 : 64 }
        }
        exit={
          (isMobile || isTablet) 
            ? { x: -256 } 
            : { opacity: 0 }
        }
        transition={{ 
          type: "spring", 
          damping: (isMobile || isTablet) ? 35 : 30, 
          stiffness: (isMobile || isTablet) ? 180 : 200
        }}
        className={cn(
          "adaptive-navigation",
          "flex flex-col h-full border-r border-border",
          // On mobile/tablet when expanded, position as overlay with solid background
          (isMobile || isTablet) && "fixed inset-y-0 left-0 z-50 w-64 shadow-lg bg-white dark:bg-gray-900 border-r border-border",
          // Desktop background
          !(isMobile || isTablet) && "bg-background",
          className
        )}
        style={{
          containerType: 'inline-size',
          containerName: 'navigation'
        }}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border bg-white dark:bg-gray-900">
          <h1 
            className={cn(
              "font-bold text-lg overflow-hidden whitespace-nowrap",
              !isExpanded && "opacity-0 w-0"
            )}
          >
            Script to Speech
          </h1>
          
          {onToggleExpanded && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onToggleExpanded}
              className="h-8 w-8 p-0 flex-shrink-0"
            >
              {isExpanded ? (
                <PanelLeftClose className="h-4 w-4" />
              ) : (
                <PanelLeftOpen className="h-4 w-4" />
              )}
            </Button>
          )}
        </div>

        {/* Navigation Items */}
        <div className="flex-1 p-2 space-y-1 bg-white dark:bg-gray-900">
          {items.map((item) => {
            const IconComponent = item.icon
            const button = (
              <Button
                key={item.id}
                variant={item.isActive ? "default" : "ghost"}
                className={cn(
                  "w-full justify-start",
                  !isExpanded && "px-2"
                )}
                onClick={item.onClick}
              >
                <IconComponent className="h-4 w-4 flex-shrink-0" />
                <span
                  className={cn(
                    "ml-2 overflow-hidden whitespace-nowrap",
                    !isExpanded && "opacity-0 w-0"
                  )}
                >
                  {item.label}
                </span>
              </Button>
            )

            if (!isExpanded) {
              return (
                <Tooltip key={item.id}>
                  <TooltipTrigger asChild>
                    {button}
                  </TooltipTrigger>
                  <TooltipContent side="right">
                    {item.label}
                  </TooltipContent>
                </Tooltip>
              )
            }

            return button
          })}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-border bg-white dark:bg-gray-900">
          <Separator className="mb-4" />
          <p 
            className={cn(
              "text-xs text-muted-foreground overflow-hidden whitespace-nowrap",
              !isExpanded && "opacity-0 w-0"
            )}
          >
            v0.1.0
          </p>
        </div>
      </motion.nav>

    </>
  )
}

export default AdaptiveNavigation