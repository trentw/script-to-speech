# TanStack Router Navigation Guide

This guide demonstrates how to use TanStack Router navigation in this codebase.

**Note:** The navigation examples below show a simplified subset of routes (`/tts`, `/screenplay`) for clarity. The actual application includes additional route groups such as `/voice-casting`, `/project`, and others. The navigation patterns shown here apply to all routes.

## Navigation Patterns

### 1. Using Link Components

Use the standard `Link` component from TanStack Router:

```typescript
import { Link } from '@tanstack/react-router';

// Basic link
<Link to="/tts">Text to Speech</Link>

// Link with params
<Link to="/screenplay/$taskId" params={{ taskId: '123' }}>
  View Task
</Link>

// Link with active styling
<Link
  to="/tts"
  activeProps={{ className: 'bg-primary text-primary-foreground' }}
>
  Text to Speech
</Link>
```

### 2. Programmatic Navigation

Use the `useNavigate` hook for programmatic navigation:

```typescript
import { useNavigate } from '@tanstack/react-router';

function MyComponent() {
  const navigate = useNavigate();

  const handleNavigation = () => {
    // Navigate to a route
    navigate({ to: '/screenplay' });

    // Navigate with params
    navigate({ to: '/screenplay/$taskId', params: { taskId: '123' } });

    // Navigate with replace (no history entry)
    navigate({ to: '/tts', replace: true });
  };
}
```

### 3. Pre-configured Link Options

For consistency, use the pre-configured link options from `lib/navigation.ts`:

```typescript
import { linkOptions } from '@/lib/navigation';

// Use pre-configured options
<Link {...linkOptions.tts}>Text to Speech</Link>
<Link {...linkOptions.screenplayTask('123')}>View Task</Link>
```

### 4. Type-Safe Navigation

Always specify the `from` parameter for better TypeScript performance:

```typescript
// ✅ Good: Include 'from' parameter
const navigate = useNavigate({ from: '/screenplay' });

// This helps TypeScript narrow types and improves IDE performance
```

## Best Practices

1. **Use Standard APIs**: Stick to TanStack Router's built-in `Link` and `useNavigate`
2. **Type Safety**: Always specify `from` when using `useNavigate`
3. **Consistency**: Use pre-configured link options for common routes
4. **Simplicity**: Avoid creating unnecessary abstractions over the router APIs
