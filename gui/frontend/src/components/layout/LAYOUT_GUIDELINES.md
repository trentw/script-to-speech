# Layout Guidelines

## Core Principle: Single Scroll Container

The application uses a **fixed frame layout** where:

- **Navigation** (left column) - Always fixed, never scrolls
- **Header** - Always fixed at top
- **Content Area** - The ONLY scrollable area

## Implementation Rules

### 1. AppShell Setup

- Root container: `h-screen overflow-hidden`
- Main content area: `overflow-auto` (NOT `overflow-hidden`)
- Grid templates use `minmax(0, 1fr)` to prevent content expansion

### 2. Route Components

All route components MUST follow this structure:

```tsx
// ✅ CORRECT
<div className="flex h-full flex-col">
  <div className="flex-shrink-0 px-6 pt-6 pb-4">
    {/* Fixed header content */}
  </div>
  <Separator className="flex-shrink-0" />
  <div className="flex-1 overflow-x-hidden overflow-y-auto">
    {/* Scrollable content */}
  </div>
</div>
```

### 3. Avoid Nested Scrolling

- **NEVER** add `overflow-y-auto` or `max-h-[*]` to child components
- If you need a scrollable section within content, use `ScrollableSection` sparingly
- Prefer letting the main content area handle all scrolling

### 4. Use ContentWrapper

For simple routes, use the ContentWrapper component:

```tsx
import { ContentWrapper } from '@/components/layout';

export function MyRoute() {
  return <ContentWrapper>{/* Your content here */}</ContentWrapper>;
}
```

### 5. Key CSS Classes

#### For fixed sections:

- `flex-shrink-0` - Prevents flexbox from shrinking the element

#### For scrollable content:

- `flex-1` - Takes remaining space in flex container
- `overflow-y-auto` - Allows vertical scrolling
- `overflow-x-hidden` - Prevents horizontal scroll

## Common Mistakes to Avoid

1. ❌ Using `min-height: 100vh` on route components
2. ❌ Adding nested `overflow-y-auto` without good reason
3. ❌ Using `max-h-[400px]` for lists (let main content scroll)
4. ❌ Forgetting `flex-shrink-0` on fixed headers/footers
5. ❌ Using `minmax(500px, 1fr)` instead of `minmax(0, 1fr)` in grid

## Testing Checklist

When adding new routes or modifying layout:

- [ ] Navigation stays fixed when scrolling content
- [ ] Header stays fixed at top
- [ ] Content scrolls smoothly without jumping
- [ ] No double scrollbars appear
- [ ] Works in both web browser and Tauri app
- [ ] Test with long content that exceeds viewport
- [ ] Test window resizing

## Platform-Specific Considerations

### Tauri Desktop App

- Test on macOS (WebKit), Windows (WebView2), Linux (WebKitGTK)
- Verify drag regions still work with fixed positioning
- Check scrollbar appearance (overlay vs gutter)

### Browser

- Test in Chrome, Firefox, Safari
- Verify responsive behavior at different viewport sizes
