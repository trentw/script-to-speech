import React from 'react'
import { motion } from 'framer-motion'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { Settings, History, Menu } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useViewportSize } from '@/hooks/useViewportSize'

interface AppHeaderProps {
  appName: string
  subAppName: string
  showNavToggle?: boolean
  onNavToggle?: () => void
  onSettingsClick?: () => void
  onHistoryClick?: () => void
  showActionButtons?: boolean
  children?: React.ReactNode
  className?: string
}

const layoutTransition = {
  type: "spring",
  damping: 25,
  stiffness: 300,
  mass: 0.8
}

export function AppHeader({
  appName,
  subAppName,
  showNavToggle = true,
  onNavToggle,
  onSettingsClick,
  onHistoryClick,
  showActionButtons = true,
  children,
  className
}: AppHeaderProps) {
  const { isMobile, isTablet } = useViewportSize()

  return (
    <header
      className={cn(
        "h-16 border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60",
        "flex items-center justify-between px-4",
        className
      )}
    >
      {/* Left Section: App Name + Nav Toggle */}
      <div className="flex items-center gap-3 min-w-0 flex-1 max-w-[60%]">
        {showNavToggle && (isMobile || isTablet) && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onNavToggle}
            className="h-9 w-9 p-0"
          >
            <Menu className="h-5 w-5" />
            <span className="sr-only">Toggle navigation</span>
          </Button>
        )}
        
        <div className="flex items-center gap-2 min-w-0">
          <h1 className="font-bold tracking-tight text-foreground truncate text-lg">
            Text to Speech
          </h1>
          
          {!isMobile && (
            <>
              <Separator orientation="vertical" className="h-6" />
              <span className="text-sm text-muted-foreground font-medium">
                {subAppName}
              </span>
            </>
          )}
        </div>
      </div>

      {/* Center Section: Provider Selector and Sub-app (Responsive) */}
      <div className={cn(
          "flex items-center gap-4",
          isMobile && "hidden" // Hide on mobile to save space
        )}>
        {children && (
          <div className="flex items-center gap-2">
            {children}
          </div>
        )}
      </div>

      {/* Right Section: Action Buttons */}
      <div className="flex items-center gap-2">
        {/* Backend Status Indicator */}
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <div className="w-2 h-2 rounded-full bg-green-500" />
          {!isMobile && <span>Connected</span>}
        </div>

        {showActionButtons && (
          <>
            <Separator orientation="vertical" className="h-6" />

            {/* Settings Button */}
            {onSettingsClick && (
              <Button
                variant="ghost"
                size="sm"
                onClick={onSettingsClick}
                className="h-9 w-9 p-0"
                title="Settings"
              >
                <Settings className="h-4 w-4" />
                <span className="sr-only">Settings</span>
              </Button>
            )}

            {/* History Button */}
            {onHistoryClick && (
              <Button
                variant="ghost"  
                size="sm"
                onClick={onHistoryClick}
                className="h-9 w-9 p-0"
                title="History"
              >
                <History className="h-4 w-4" />
                <span className="sr-only">History</span>
              </Button>
            )}
          </>
        )}
      </div>
    </header>
  )
}

export default AppHeader