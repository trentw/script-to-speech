import React, { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Tabs, TabsList, TabsTrigger } from './tabs';
import { cn } from '@/lib/utils';

export interface AnimatedTabsProps {
  defaultValue?: string;
  value?: string;
  onValueChange?: (value: string) => void;
  className?: string;
  children: React.ReactNode;
}

export interface AnimatedTabsContentProps {
  value: string;
  className?: string;
  children: React.ReactNode;
}

// Context to track tab direction
const TabsContext = React.createContext<{
  activeTab: string;
  direction: number;
  setActiveTab: (value: string) => void;
}>({
  activeTab: '',
  direction: 0,
  setActiveTab: () => {},
});

export function AnimatedTabs({ 
  defaultValue = '', 
  value, 
  onValueChange, 
  className, 
  children 
}: AnimatedTabsProps) {
  const [internalValue, setInternalValue] = useState(defaultValue);
  const [direction, setDirection] = useState(0);
  
  const activeTab = value !== undefined ? value : internalValue;
  
  // Extract tab order for direction calculation - use fixed order for Settings/History
  const tabOrder = ['settings', 'history'];

  const setActiveTab = useCallback((newValue: string) => {
    const currentIndex = tabOrder.indexOf(activeTab);
    const newIndex = tabOrder.indexOf(newValue);
    setDirection(newIndex > currentIndex ? 1 : -1);
    
    if (value === undefined) {
      setInternalValue(newValue);
    }
    onValueChange?.(newValue);
  }, [activeTab, tabOrder, value, onValueChange]);

  return (
    <TabsContext.Provider value={{ activeTab, direction, setActiveTab }}>
      <Tabs 
        value={activeTab} 
        onValueChange={setActiveTab}
        className={cn("flex flex-col", className)}
      >
        {children}
      </Tabs>
    </TabsContext.Provider>
  );
}

export function AnimatedTabsList({ 
  className, 
  children, 
  ...props 
}: React.ComponentProps<typeof TabsList>) {
  return (
    <TabsList 
      className={cn(
        // Ultra-clean styling with no border, exactly matching reference design
        "h-auto bg-transparent p-0 gap-6",
        className
      )} 
      {...props}
    >
      {children}
    </TabsList>
  );
}

export function AnimatedTabsTrigger({ 
  className, 
  children, 
  ...props 
}: React.ComponentProps<typeof TabsTrigger>) {
  return (
    <TabsTrigger 
      className={cn(
        // Ultra-minimal styling exactly matching reference design
        "relative bg-transparent border-0 rounded-none px-0 py-3 text-base font-normal",
        // Much more greyed out inactive tabs, exactly like reference
        "text-muted-foreground/30 hover:text-muted-foreground/60 transition-all duration-200",
        // Active state with thick underline
        "data-[state=active]:bg-transparent data-[state=active]:text-foreground data-[state=active]:font-medium",
        "data-[state=active]:shadow-none",
        // Thick dark underline for active state
        "border-b-2 border-transparent data-[state=active]:border-foreground",
        "cursor-pointer select-none focus:outline-none",
        className
      )} 
      {...props}
    >
      {children}
    </TabsTrigger>
  );
}

export function AnimatedTabsContent({ 
  value, 
  className, 
  children 
}: AnimatedTabsContentProps) {
  const { activeTab, direction } = React.useContext(TabsContext);
  const isActive = activeTab === value;

  if (!isActive) return null;

  return (
    <div className={cn("flex-1 overflow-hidden min-h-0 relative", className)}>
      <AnimatePresence mode="wait" custom={direction}>
        <motion.div
          key={value}
          custom={direction}
          initial={{ x: direction > 0 ? 300 : -300, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: direction > 0 ? -300 : 300, opacity: 0 }}
          transition={{
            duration: 0.3,
            ease: [0.4, 0, 0.2, 1], // Custom bezier for smooth feel
          }}
          className="absolute inset-0"
        >
          {children}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}

// Export compound component
AnimatedTabs.List = AnimatedTabsList;
AnimatedTabs.Trigger = AnimatedTabsTrigger;
AnimatedTabs.Content = AnimatedTabsContent;