import React from 'react'
import {
  Drawer,
  DrawerContent,
  DrawerHeader,
  DrawerTitle,
} from '@/components/ui/drawer'
import { cn } from '@/lib/utils'

interface MobileDrawerProps {
  isOpen: boolean
  onClose: () => void
  title: string
  children: React.ReactNode
  className?: string
}

export function MobileDrawer({
  isOpen,
  onClose,
  title,
  children,
  className
}: MobileDrawerProps) {
  return (
    <Drawer open={isOpen} onOpenChange={onClose}>
      <DrawerContent 
        className={cn(
          "h-[90vh] bg-white dark:bg-gray-900 border-border shadow-lg",
          className
        )}
      >
        <DrawerHeader className="border-b border-border bg-white dark:bg-gray-900">
          <DrawerTitle className="text-foreground font-semibold">{title}</DrawerTitle>
        </DrawerHeader>
        <div className="flex-1 overflow-y-auto p-4 bg-white dark:bg-gray-900">
          {children}
        </div>
      </DrawerContent>
    </Drawer>
  )
}

export default MobileDrawer