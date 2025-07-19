import { cva } from "class-variance-authority"

/**
 * Extended button variants for Script to Speech application
 * These variants extend the base shadcn/ui Button component with 
 * application-specific styling patterns for consistent UI
 */

// Common hover states for action buttons
export const actionButtonHover = "hover:bg-accent hover:text-accent-foreground transition-colors"

// Standardized icon button sizes
export const iconButtonSizes = {
  sm: "h-7 w-7", // Small actions (history items, voice preview)
  default: "h-9 w-9", // Standard icon buttons
  md: "h-12 w-12", // Medium controls (audio player)
  lg: "h-16 w-16", // Large controls
  xl: "h-20 w-20", // Extra large (main play button)
}

// Application-specific button variants
export const appButtonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap text-sm font-medium transition-all duration-200 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg:not([class*='size-'])]:size-4 [&_svg]:shrink-0 outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 cursor-pointer select-none",
  {
    variants: {
      variant: {
        // Primary action button (generate speech) - inverted for prominence
        primary: "bg-gray-900 text-white hover:bg-gray-800 hover:shadow-lg active:scale-95 active:shadow-inner shadow-md rounded-md",
        
        // Secondary action button - standard colors
        secondary: "bg-background text-foreground border border-border hover:bg-gray-100 hover:text-foreground hover:border-gray-300 active:scale-95 active:shadow-inner shadow-sm rounded-md",
        
        // Audio control buttons
        "audio-control": "bg-transparent hover:bg-gray-100 hover:text-foreground rounded-full hover:shadow-md active:scale-95 active:shadow-inner",
        
        // Audio play button (main) - CIRCULAR inverted button for prominence
        "audio-play": "bg-gray-900 text-white hover:bg-gray-800 hover:shadow-xl active:scale-95 active:shadow-inner shadow-lg rounded-full border-2 border-gray-900",
        
        // Action buttons in lists (play, download, more) - more prominent hover
        "list-action": "bg-transparent hover:bg-gray-200 hover:text-foreground hover:shadow-md active:scale-95 active:shadow-inner transition-all rounded-md",
        
        // Reset/secondary buttons
        "reset": "border border-border bg-background hover:bg-gray-100 hover:text-foreground hover:shadow-md active:scale-95 active:shadow-inner rounded-md",
        
        // Sidebar toggle
        "sidebar-toggle": "hover:bg-gray-100 hover:text-foreground hover:shadow-md active:scale-95 active:shadow-inner rounded-md",
        
        // Provider/voice selection
        "selection": "border border-border bg-background hover:bg-gray-100 hover:text-foreground hover:border-gray-300 hover:shadow-md active:scale-95 active:shadow-inner rounded-md",
      },
      size: {
        sm: "h-8 px-3 text-xs",
        default: "h-9 px-4 py-2",
        lg: "h-10 px-8",
        icon: "h-9 w-9",
        "icon-sm": "h-7 w-7",
        "icon-md": "h-12 w-12",
        "icon-lg": "h-16 w-16",
        "icon-xl": "h-20 w-20",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "default",
    },
  }
)

// Button styling utilities
export const buttonUtils = {
  // Consistent focus styles
  focusRing: "focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
  
  // Standard transition
  transition: "transition-colors duration-200",
  
  // Icon sizing for buttons
  iconSizing: "[&_svg]:pointer-events-none [&_svg:not([class*='size-'])]:size-4 [&_svg]:shrink-0",
  
  // Disabled state
  disabled: "disabled:pointer-events-none disabled:opacity-50",
}

// Semantic button types for common use cases
export const semanticButtons = {
  // Audio player controls
  audioPlay: "icon-xl audio-play",
  audioControl: "icon-md audio-control",
  audioSmall: "icon-sm audio-control",
  
  // List action buttons
  listPlay: "icon-sm list-action",
  listDownload: "icon-sm list-action",
  listMore: "icon-sm list-action",
  
  // Form buttons
  generate: "lg primary",
  reset: "default reset",
  
  // Navigation
  sidebarToggle: "icon sidebar-toggle",
  back: "icon-sm list-action",
}

export type AppButtonVariant = "primary" | "secondary" | "audio-control" | "audio-play" | "list-action" | "reset" | "sidebar-toggle" | "selection"
export type AppButtonSize = "sm" | "default" | "lg" | "icon" | "icon-sm" | "icon-md" | "icon-lg" | "icon-xl"