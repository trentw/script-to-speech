# Frontend Testing Guide

This guide covers testing patterns, conventions, and best practices for the Script-to-Speech frontend.

## Quick Start

```bash
# Run all tests
pnpm test

# Run tests in watch mode (recommended during development)
pnpm test:watch

# Run tests with coverage
pnpm test:coverage

# Open the Vitest UI (best for debugging)
pnpm test:ui

# Run tests for a specific file
pnpm test AudioPlayer

# Run tests matching a pattern
pnpm test --grep "should handle errors"

# Clear test cache if you see stale results
pnpm test:clearCache
```

## Testing Strategy for Code in Flux

When testing a codebase that's actively evolving, it's important to be strategic about what to test and when:

### Focus on Stable, High-Value Areas

1. **Custom Hooks**: These encapsulate business logic and are less likely to change
2. **Layout Components**: Structure and responsive behavior tend to be stable
3. **Utility Functions**: Pure functions with clear inputs/outputs
4. **API Integration**: The contract between frontend and backend

### When to Add Tests vs When to Wait

**Add Tests When:**

- The component/hook has stabilized and isn't likely to change significantly
- It contains critical business logic that needs protection
- It's a reusable component that other parts depend on
- You're fixing a bug (add a test to prevent regression)

**Wait to Test When:**

- The UI is still being actively redesigned
- Requirements are unclear or changing frequently
- It's a prototype or experimental feature
- The implementation approach is still being validated

### Example: Testing Stable Hooks

```typescript
// Hooks like useVoiceLibrary are stable and high-value to test
it('should fetch voice library data on mount', async () => {
  const { result } = renderHook(() => useVoiceLibrary('openai'));

  // Initially loading
  expect(result.current.isLoading).toBe(true);

  // Wait for data
  await waitFor(() => {
    expect(result.current.data).toEqual(mockVoiceData);
  });
});
```

## Test Structure

We follow the **Arrange/Act/Assert** pattern from our Python testing:

```typescript
it('should handle click events', async () => {
  // Arrange
  const user = userEvent.setup()
  const handleClick = vi.fn()
  render(<Button onClick={handleClick}>Click me</Button>)

  // Act
  await user.click(screen.getByRole('button'))

  // Assert
  expect(handleClick).toHaveBeenCalledTimes(1)
})
```

## File Organization

```
src/
├── components/
│   ├── __tests__/        # Integration tests for complex components
│   │   └── AudioPlayer.test.tsx
│   └── ui/
│       └── __tests__/    # Unit tests for UI components
│           └── button.test.tsx
├── hooks/
│   └── __tests__/        # Hook tests
│       └── useProviders.test.ts
├── stores/
│   └── __tests__/        # Store tests
│       └── appStore.test.ts
└── test/                 # Test utilities and setup
    ├── mocks/           # MSW handlers and mock data
    ├── utils/           # Test helpers
    └── setup.ts         # Global test setup
```

## Testing Patterns

### Component Tests

Use our custom render utility that includes all providers:

```typescript
import { render, screen } from '@/test/utils/render'

// Basic render
render(<MyComponent />)

// With props
render(<MyComponent prop="value" />)

// With preloaded state
render(<MyComponent />, {
  preloadedState: {
    selectedProvider: 'openai',
    selectedVoice: 'alloy'
  }
})
```

### User Interactions

Always use `userEvent` for simulating user interactions:

```typescript
import userEvent from '@testing-library/user-event';

const user = userEvent.setup();

// Click
await user.click(button);

// Type
await user.type(input, 'Hello');

// Select
await user.selectOptions(select, 'option-value');

// Keyboard
await user.keyboard('{Enter}');
```

### Async Operations

Use `findBy` queries and `waitFor` for async operations:

```typescript
// Wait for element to appear
const element = await screen.findByText('Loaded');

// Wait for assertion
await waitFor(() => {
  expect(mockFn).toHaveBeenCalled();
});

// Wait with custom timeout
await screen.findByText('Loaded', { timeout: 3000 });
```

### API Mocking

We use MSW (Mock Service Worker) for API mocking:

```typescript
import { http, HttpResponse } from 'msw';
import { server } from '@/test/mocks/server';

// Override handler for specific test
server.use(
  http.get('/api/providers/info', () => {
    return HttpResponse.json({ error: 'Server error' }, { status: 500 });
  })
);

// Reset handlers after test
afterEach(() => {
  server.resetHandlers();
});
```

### Store Testing

Test stores in isolation with fresh instances:

```typescript
import { createTestStore } from '@/test/utils/createStore';

it('should update provider', () => {
  // Arrange
  const store = createTestStore();

  // Act
  store.getState().setSelectedProvider('elevenlabs');

  // Assert
  expect(store.getState().selectedProvider).toBe('elevenlabs');
});
```

### Hook Testing

Use `renderHook` with our custom wrapper:

```typescript
import { renderHook, waitFor } from '@/test/utils/render';

const { result } = renderHook(() => useProviders());

await waitFor(() => {
  expect(result.current.data).toBeDefined();
});
```

#### Advanced Hook Testing Patterns

**Testing Hooks with Parameters:**

```typescript
it('should update when provider changes', async () => {
  const { result, rerender } = renderHook(
    ({ provider }) => useVoiceLibrary(provider),
    { initialProps: { provider: 'openai' } }
  );

  // Initial load
  await waitFor(() => expect(result.current.data).toBeDefined());
  expect(result.current.data?.voices).toHaveLength(6);

  // Change provider
  rerender({ provider: 'elevenlabs' });

  // Should refetch with new provider
  await waitFor(() => {
    expect(result.current.data?.voices).toHaveLength(3);
  });
});
```

**Testing Polling Hooks with Timers:**

```typescript
beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.restoreRealTimers();
});

it('should poll for updates at specified interval', async () => {
  const mockTasks = [
    { id: '1', status: 'processing' },
    { id: '1', status: 'completed' },
  ];

  let callCount = 0;
  server.use(
    http.get('/api/tasks', () => {
      return HttpResponse.json(mockTasks[callCount++ % 2]);
    })
  );

  const { result } = renderHook(() => useTaskPolling('1', 1000));

  // Initial state
  await waitFor(() => {
    expect(result.current.data?.status).toBe('processing');
  });

  // Advance timer to trigger next poll
  await act(async () => {
    vi.advanceTimersByTime(1000);
  });

  // Should have updated status
  await waitFor(() => {
    expect(result.current.data?.status).toBe('completed');
  });
});
```

**Testing Hook Cleanup:**

```typescript
it('should cleanup on unmount', async () => {
  const mockStop = vi.fn();
  vi.mocked(window.Audio).mockImplementation(() => ({
    play: vi.fn(),
    pause: mockStop,
    // ... other properties
  }));

  const { result, unmount } = renderHook(() => useAudio());

  // Start playing
  await act(async () => {
    await result.current.play('test.mp3');
  });

  // Unmount should stop audio
  unmount();
  expect(mockStop).toHaveBeenCalled();
});
```

**Testing Hook Error States:**

```typescript
it('should handle API errors gracefully', async () => {
  server.use(
    http.get('/api/providers/info', () => {
      return HttpResponse.json({ error: 'Server error' }, { status: 500 });
    })
  );

  const { result } = renderHook(() => useProviders());

  await waitFor(() => {
    expect(result.current.isError).toBe(true);
    expect(result.current.error).toBeDefined();
  });
});
```

## Layout Component Testing

Layout components require special attention to responsive behavior and styling:

### Testing Responsive Behavior

```typescript
it('should adapt layout for mobile screens', () => {
  // Set mobile viewport
  global.innerWidth = 375
  global.innerHeight = 667

  const { container } = render(<AppLayout />)

  // Check mobile-specific classes
  expect(container.firstChild).toHaveClass('flex-col')
  expect(screen.queryByRole('complementary')).not.toBeInTheDocument() // Sidebar hidden
})

it('should show sidebar on desktop', () => {
  // Set desktop viewport
  global.innerWidth = 1440
  global.innerHeight = 900

  render(<AppLayout />)

  // Sidebar should be visible
  expect(screen.getByRole('complementary')).toBeInTheDocument()
})
```

### Testing CSS Classes and Styling

```typescript
it('should apply correct styling classes', () => {
  const { container } = render(<MainLayout />)

  const main = screen.getByRole('main')
  expect(main).toHaveClass(
    'flex-1',
    'p-6',
    'lg:p-8',
    'overflow-y-auto'
  )

  // Test dynamic classes
  expect(container.firstChild).toHaveClass('min-h-screen', 'bg-background')
})
```

### Testing Layout Structure

```typescript
it('should render correct layout hierarchy', () => {
  render(<AppLayout />)

  // Header should be at the top
  const header = screen.getByRole('banner')
  expect(header.parentElement).toHaveClass('sticky', 'top-0', 'z-50')

  // Main content area
  const main = screen.getByRole('main')
  expect(main).toBeInTheDocument()

  // Footer at the bottom
  const footer = screen.getByRole('contentinfo')
  expect(footer).toBeInTheDocument()
})
```

### Testing Layout with Different Content States

```typescript
it('should handle empty state gracefully', () => {
  render(
    <MainLayout>
      <EmptyState />
    </MainLayout>
  )

  expect(screen.getByText('No content available')).toBeInTheDocument()
  expect(screen.getByRole('main')).toHaveClass('flex', 'items-center', 'justify-center')
})

it('should handle loading state', () => {
  render(
    <MainLayout isLoading>
      <div>Content</div>
    </MainLayout>
  )

  expect(screen.getByRole('progressbar')).toBeInTheDocument()
  expect(screen.queryByText('Content')).not.toBeInTheDocument()
})
```

### Testing Accessibility in Layouts

```typescript
it('should have proper landmark roles', () => {
  render(<AppLayout />)

  // All major landmarks should be present
  expect(screen.getByRole('banner')).toBeInTheDocument() // header
  expect(screen.getByRole('navigation')).toBeInTheDocument() // nav
  expect(screen.getByRole('main')).toBeInTheDocument() // main
  expect(screen.getByRole('complementary')).toBeInTheDocument() // aside
  expect(screen.getByRole('contentinfo')).toBeInTheDocument() // footer
})

it('should maintain focus management', async () => {
  const user = userEvent.setup()
  render(<AppLayout />)

  // Tab through major sections
  await user.tab()
  expect(screen.getByRole('navigation')).toHaveFocus()

  await user.tab()
  expect(screen.getByRole('main')).toHaveFocus()
})
```

## Accessibility Testing

Every component should include accessibility tests:

```typescript
import { axe } from 'vitest-axe'

it('should not have accessibility violations', async () => {
  const { container } = render(<Button>Click me</Button>)
  const results = await axe(container)
  expect(results).toHaveNoViolations()
})
```

**Note**: Some accessibility tests are currently skipped due to jsdom limitations with canvas. See `src/components/ui/__tests__/button.test.tsx` for details.

## Integration vs Unit Tests

Understanding when to write integration tests versus unit tests helps create a balanced test suite:

### Unit Tests

**When to Use:**

- Testing individual functions or components in isolation
- Testing pure logic without external dependencies
- Testing specific edge cases or error conditions
- When you need fast, focused feedback

**Examples:**

```typescript
// Unit test for a utility function
describe('formatDuration', () => {
  it('should format seconds into MM:SS', () => {
    expect(formatDuration(65)).toBe('1:05')
    expect(formatDuration(3600)).toBe('60:00')
  })
})

// Unit test for a simple component
it('should render button with correct text', () => {
  render(<Button>Click me</Button>)
  expect(screen.getByRole('button')).toHaveTextContent('Click me')
})

// Unit test for store action
it('should update selected provider', () => {
  const store = createTestStore()
  store.getState().setSelectedProvider('elevenlabs')
  expect(store.getState().selectedProvider).toBe('elevenlabs')
})
```

### Integration Tests

**When to Use:**

- Testing how multiple components work together
- Testing complete user workflows
- Testing API integration with components
- Verifying that the system works end-to-end

**Examples:**

```typescript
// Integration test for form submission flow
it('should complete audio generation workflow', async () => {
  const user = userEvent.setup()
  render(<App />)

  // User fills out form
  await user.type(screen.getByLabelText('Text'), 'Hello world')
  await user.selectOptions(screen.getByLabelText('Provider'), 'openai')
  await user.selectOptions(screen.getByLabelText('Voice'), 'alloy')

  // Submit form
  await user.click(screen.getByRole('button', { name: 'Generate' }))

  // Wait for task to complete
  await waitFor(() => {
    expect(screen.getByText('Status: completed')).toBeInTheDocument()
  }, { timeout: 10000 })

  // Audio player should appear
  expect(screen.getByRole('button', { name: 'Play' })).toBeInTheDocument()
})

// Integration test for data flow through hooks and components
it('should update voice options when provider changes', async () => {
  const user = userEvent.setup()
  render(<ConfigurationPanel />)

  // Initially shows OpenAI voices
  expect(screen.getByRole('option', { name: 'alloy' })).toBeInTheDocument()

  // Change provider
  await user.selectOptions(screen.getByLabelText('Provider'), 'elevenlabs')

  // Should fetch and display ElevenLabs voices
  await waitFor(() => {
    expect(screen.getByRole('option', { name: 'Rachel' })).toBeInTheDocument()
    expect(screen.queryByRole('option', { name: 'alloy' })).not.toBeInTheDocument()
  })
})
```

### Choosing the Right Approach

**Use Unit Tests for:**

- **Speed**: Need to run hundreds of tests quickly
- **Isolation**: Testing specific behavior without setup complexity
- **Edge Cases**: Testing error conditions that are hard to trigger in integration
- **Refactoring**: Ensuring internal changes don't break functionality

**Use Integration Tests for:**

- **Confidence**: Ensuring the system works as users expect
- **Workflows**: Testing multi-step processes
- **API Integration**: Verifying frontend/backend communication
- **Regression Prevention**: Catching issues unit tests might miss

### Trade-offs

| Aspect               | Unit Tests      | Integration Tests |
| -------------------- | --------------- | ----------------- |
| **Speed**            | Fast (ms)       | Slower (seconds)  |
| **Isolation**        | High            | Low               |
| **Debugging**        | Easy            | More complex      |
| **Confidence**       | Component works | System works      |
| **Maintenance**      | Low             | Higher            |
| **Setup Complexity** | Simple          | More complex      |

### Best Practice: Testing Pyramid

Follow the testing pyramid approach:

```
       /\
      /  \  E2E Tests (Few)
     /    \
    /------\  Integration Tests (Some)
   /        \
  /----------\  Unit Tests (Many)
```

- **Many Unit Tests**: Fast feedback, easy to maintain
- **Some Integration Tests**: Verify component interactions
- **Few E2E Tests**: Validate critical user paths

## Common Queries

Prefer accessible queries in this order:

1. **ByRole**: `screen.getByRole('button', { name: 'Submit' })`
2. **ByLabelText**: `screen.getByLabelText('Email')`
3. **ByPlaceholderText**: `screen.getByPlaceholderText('Enter email')`
4. **ByText**: `screen.getByText('Welcome')`
5. **ByTestId**: `screen.getByTestId('custom-element')` (last resort)

## Testing Library Queries Reference

| Query Type  | When to Use           | Example                      |
| ----------- | --------------------- | ---------------------------- |
| `getBy*`    | Element exists        | `getByRole('button')`        |
| `queryBy*`  | Element may not exist | `queryByText('Error')`       |
| `findBy*`   | Element appears async | `await findByText('Loaded')` |
| `getAllBy*` | Multiple elements     | `getAllByRole('listitem')`   |

## Mocking Best Practices

### Mock at the Network Boundary

```typescript
// Good: Mock API responses with MSW
http.get('/api/data', () => HttpResponse.json({ data }));

// Avoid: Mocking modules directly
vi.mock('@/services/api');
```

### Keep Mocks Minimal

```typescript
// Good: Mock only what the component uses
const mockAudio = {
  play: vi.fn(() => Promise.resolve()),
  pause: vi.fn(),
  currentTime: 0,
  duration: 120,
};

// Avoid: Complete interface mocks when unnecessary
```

### Test Data Factories

Use factories for consistent test data:

```typescript
import { createMockProvider, createMockTask } from '@/test/utils/test-data';

const provider = createMockProvider({ name: 'openai' });
const task = createMockTask({ status: 'completed' });
```

## Debugging Tests

### Vitest UI

Best way to debug tests interactively:

```bash
pnpm test:ui
```

### Debug Output

```typescript
// Print the DOM
screen.debug();

// Print specific element
screen.debug(screen.getByRole('button'));

// Log queries available
screen.logTestingPlaygroundURL();
```

### Common Issues

#### "Not wrapped in act(...)"

This usually means a state update happened after the test finished:

```typescript
// Fix: Wait for all updates to complete
await waitFor(() => {
  expect(screen.getByText('Updated')).toBeInTheDocument();
});
```

#### "Unable to find element"

Check the query and use `screen.debug()`:

```typescript
// Debug what's rendered
screen.debug();

// Use more specific queries
screen.getByRole('button', { name: 'Specific Button' });
```

#### Test Timeouts

Increase timeout for specific tests:

```typescript
it('should handle slow operations', async () => {
  // test code
}, 10000); // 10 second timeout
```

## Performance Tips

1. **Use `screen` imports**: Import queries from screen for better performance
2. **Avoid `container` queries**: Use `screen` queries instead
3. **Mock heavy operations**: Mock file I/O, network requests, and timers
4. **Use `vi.mock` sparingly**: Prefer MSW for network mocks

## Test Coverage

Current thresholds (80% for all metrics):

- Lines
- Functions
- Branches
- Statements

Check coverage report:

```bash
pnpm test:coverage
open coverage/index.html
```

## CI Integration

Tests run automatically on:

- Pre-commit hooks (via `.pre-commit-config.yaml`)
- Pull requests
- Main branch pushes

To skip pre-commit tests temporarily:

```bash
git commit --no-verify -m "WIP: Skip tests"
```

## Common Testing Scenarios

### Testing Loading States

```typescript
it('should show loading state while fetching data', async () => {
  render(<ProviderList />)

  // Initially shows loading
  expect(screen.getByText('Loading providers...')).toBeInTheDocument()

  // Wait for data to load
  await waitFor(() => {
    expect(screen.queryByText('Loading providers...')).not.toBeInTheDocument()
  })

  // Data is displayed
  expect(screen.getByText('OpenAI')).toBeInTheDocument()
})
```

### Testing Complex State Transitions

```typescript
it('should handle task lifecycle from creation to completion', async () => {
  const user = userEvent.setup()
  vi.useFakeTimers()

  render(<TaskManager />)

  // Create task
  await user.click(screen.getByRole('button', { name: 'Create Task' }))

  // Should show processing state
  expect(screen.getByText('Status: processing')).toBeInTheDocument()

  // Simulate time passing for polling
  await act(async () => {
    vi.advanceTimersByTime(2000)
  })

  // Should update to completed
  await waitFor(() => {
    expect(screen.getByText('Status: completed')).toBeInTheDocument()
  })

  vi.restoreRealTimers()
})
```

### Testing Data Synchronization

```typescript
it('should sync store state with API data', async () => {
  const store = createTestStore()
  render(<App />, { store })

  // Wait for providers to load
  await waitFor(() => {
    expect(screen.getByText('OpenAI')).toBeInTheDocument()
  })

  // Store should be updated with default provider
  expect(store.getState().selectedProvider).toBe('openai')

  // User changes provider
  const user = userEvent.setup()
  await user.selectOptions(screen.getByLabelText('Provider'), 'elevenlabs')

  // Store should reflect the change
  expect(store.getState().selectedProvider).toBe('elevenlabs')
})
```

### Testing Error States

```typescript
it('should handle API errors gracefully', async () => {
  // Override the handler to return an error
  server.use(
    http.get('/api/providers/info', () => {
      return HttpResponse.json(
        { error: 'Internal server error' },
        { status: 500 }
      )
    })
  )

  render(<ProviderList />)

  await waitFor(() => {
    expect(screen.getByText(/Failed to load providers/)).toBeInTheDocument()
  })
})
```

### Testing Form Submissions

```typescript
it('should submit form with correct data', async () => {
  const user = userEvent.setup()
  render(<GenerateAudioForm />)

  // Fill form
  await user.type(screen.getByLabelText('Text to convert'), 'Hello world')
  await user.selectOptions(screen.getByLabelText('Provider'), 'openai')
  await user.selectOptions(screen.getByLabelText('Voice'), 'alloy')

  // Submit
  await user.click(screen.getByRole('button', { name: 'Generate Audio' }))

  // Verify API was called correctly
  await waitFor(() => {
    expect(screen.getByText('Audio generation started')).toBeInTheDocument()
  })
})
```

### Testing Real-time Updates (Polling)

```typescript
it('should poll for task status updates', async () => {
  const { rerender } = render(<TaskStatus taskId="123" />)

  // Initial status
  expect(screen.getByText('Status: processing')).toBeInTheDocument()

  // Wait for polling to fetch updated status
  await waitFor(() => {
    expect(screen.getByText('Status: completed')).toBeInTheDocument()
  }, { timeout: 5000 })
})
```

### Testing Store Updates

```typescript
it('should update store when provider is selected', async () => {
  const user = userEvent.setup()
  const store = createTestStore()

  render(<ProviderSelector />, { store })

  await user.selectOptions(screen.getByRole('combobox'), 'elevenlabs')

  expect(store.getState().selectedProvider).toBe('elevenlabs')
})
```

### Testing Keyboard Navigation

```typescript
it('should support keyboard navigation', async () => {
  const user = userEvent.setup()
  render(<VoiceSelector />)

  const combobox = screen.getByRole('combobox')
  await user.click(combobox)

  // Navigate with keyboard
  await user.keyboard('{ArrowDown}')
  await user.keyboard('{ArrowDown}')
  await user.keyboard('{Enter}')

  expect(combobox).toHaveValue('echo')
})
```

### Testing Error Handling Patterns

```typescript
// Testing network errors
it('should handle network failures gracefully', async () => {
  server.use(
    http.get('/api/providers/info', () => {
      return HttpResponse.error()
    })
  )

  render(<ProviderSelector />)

  await waitFor(() => {
    expect(screen.getByText(/Failed to load providers/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument()
  })
})

// Testing validation errors
it('should show validation errors for invalid input', async () => {
  const user = userEvent.setup()
  render(<AudioGenerationForm />)

  // Submit without required fields
  await user.click(screen.getByRole('button', { name: 'Generate' }))

  expect(screen.getByText('Text is required')).toBeInTheDocument()
  expect(screen.getByText('Please select a provider')).toBeInTheDocument()
})

// Testing error recovery
it('should recover from errors when user retries', async () => {
  const user = userEvent.setup()
  let attemptCount = 0

  server.use(
    http.get('/api/providers/info', () => {
      attemptCount++
      if (attemptCount === 1) {
        return HttpResponse.error()
      }
      return HttpResponse.json({ providers: mockProviders })
    })
  )

  render(<ProviderList />)

  // First attempt fails
  await waitFor(() => {
    expect(screen.getByText(/Failed to load/)).toBeInTheDocument()
  })

  // User retries
  await user.click(screen.getByRole('button', { name: 'Retry' }))

  // Second attempt succeeds
  await waitFor(() => {
    expect(screen.getByText('OpenAI')).toBeInTheDocument()
    expect(screen.queryByText(/Failed to load/)).not.toBeInTheDocument()
  })
})
```

## MSW (Mock Service Worker) Patterns

### Creating Reusable Handlers

```typescript
// src/test/mocks/handlers.ts
export const createTaskHandlers = (overrides = {}) => [
  http.post('/api/tasks', async ({ request }) => {
    const body = await request.json();
    return HttpResponse.json({
      id: 'task-123',
      status: 'processing',
      ...overrides,
      ...body,
    });
  }),
];
```

### Testing Different Response Scenarios

```typescript
// Success case
it('should handle successful response', async () => {
  // Default handlers return success
  render(<MyComponent />)
  // ... test success flow
})

// Error case
it('should handle server errors', async () => {
  server.use(
    http.get('/api/data', () => {
      return new HttpResponse(null, { status: 500 })
    })
  )
  render(<MyComponent />)
  // ... test error flow
})

// Network failure
it('should handle network failures', async () => {
  server.use(
    http.get('/api/data', () => {
      return HttpResponse.error()
    })
  )
  render(<MyComponent />)
  // ... test network error flow
})
```

### Intercepting and Asserting Requests

```typescript
it('should send correct request payload', async () => {
  let capturedRequest: any

  server.use(
    http.post('/api/tasks', async ({ request }) => {
      capturedRequest = await request.json()
      return HttpResponse.json({ id: '123' })
    })
  )

  // Trigger the request
  render(<CreateTaskForm />)
  await userEvent.click(screen.getByRole('button', { name: 'Create' }))

  // Assert request payload
  await waitFor(() => {
    expect(capturedRequest).toEqual({
      text: 'Expected text',
      provider: 'openai',
      voice: 'alloy',
    })
  })
})
```

## Debugging Tips

### Using Vitest UI

The Vitest UI is the best tool for debugging tests:

1. Run `pnpm test:ui`
2. Click on a failing test to see:
   - Full error stack trace
   - Test code with inline results
   - Console output
   - Module graph

### Debug Logging in Tests

```typescript
it('should work correctly', async () => {
  render(<MyComponent />)

  // Log the entire DOM
  screen.debug()

  // Log a specific element
  const button = screen.getByRole('button')
  screen.debug(button)

  // Log available queries
  screen.logTestingPlaygroundURL()

  // Use console.log for values
  console.log('Store state:', store.getState())
})
```

### Common Debugging Strategies

1. **Element not found**: Use `screen.debug()` to see what's rendered
2. **Timing issues**: Increase `waitFor` timeout or add custom waits
3. **State not updating**: Check if you're using the correct store instance
4. **MSW not intercepting**: Verify the URL and method match exactly

## Best Practices Checklist

- ✅ Use `userEvent` over `fireEvent` for user interactions
- ✅ Prefer `findBy` queries for async elements
- ✅ Use accessible queries (byRole, byLabelText) over test IDs
- ✅ Mock at the network boundary with MSW, not modules
- ✅ Test user behavior, not implementation details
- ✅ Include accessibility checks in component tests
- ✅ Keep test data factories up to date with types
- ✅ Clear server handlers after each test
- ✅ Use descriptive test names that explain the scenario

## Performance Optimization

### Speeding Up Tests

1. **Mock heavy operations**:

   ```typescript
   vi.mock('@/utils/audio', () => ({
     processAudio: vi.fn(() => Promise.resolve()),
   }));
   ```

2. **Use test.concurrent for independent tests**:

   ```typescript
   test.concurrent('test 1', async () => {
     /* ... */
   });
   test.concurrent('test 2', async () => {
     /* ... */
   });
   ```

3. **Minimize waitFor timeouts**:

   ```typescript
   // Bad: Always waits 1 second
   await waitFor(() => expect(element).toBeInTheDocument(), { timeout: 1000 });

   // Good: Returns as soon as condition is met
   await screen.findByText('Loaded');
   ```

## Gotchas and Lessons Learned

### Common Pitfalls

1. **Timer-based Polling Tests**

   ```typescript
   // Bad: Forgetting to use fake timers
   it('should poll for updates', async () => {
     render(<PollingComponent />)
     // This will actually wait 5 seconds!
     await waitFor(() => expect(mockFn).toHaveBeenCalledTimes(5), { timeout: 5000 })
   })

   // Good: Use fake timers
   beforeEach(() => vi.useFakeTimers())
   afterEach(() => vi.restoreRealTimers())
   ```

2. **Store State Persistence**

   ```typescript
   // Bad: Tests affecting each other through persisted state
   it('test 1', () => {
     store.setState({ provider: 'openai' });
   });

   it('test 2', () => {
     // This might start with 'openai' from previous test!
   });

   // Good: Use fresh store instances
   it('test 2', () => {
     const store = createTestStore(); // Fresh store
   });
   ```

3. **Async State Updates**

   ```typescript
   // Bad: Not waiting for async updates
   it('should update after API call', () => {
     render(<Component />)
     fireEvent.click(button)
     expect(screen.getByText('Updated')).toBeInTheDocument() // Might fail!
   })

   // Good: Wait for updates
   it('should update after API call', async () => {
     render(<Component />)
     await user.click(button)
     await waitFor(() => {
       expect(screen.getByText('Updated')).toBeInTheDocument()
     })
   })
   ```

### Testing Code in Flux

When working with evolving code:

1. **Focus on Interfaces, Not Implementation**
   - Test what users see and do, not how it works internally
   - This makes tests more resilient to refactoring

2. **Use Data Attributes Sparingly**
   - Prefer accessible queries that won't change
   - Only use `data-testid` when no semantic option exists

3. **Mock at Stable Boundaries**
   - Mock at the API level (MSW) rather than modules
   - This allows internal refactoring without breaking tests

4. **Write Tests That Tell a Story**

   ```typescript
   it('should allow users to generate audio from text', async () => {
     // User opens the app
     render(<App />)

     // User enters their text
     await user.type(screen.getByLabelText('Text to convert'), 'Hello world')

     // User configures their preferences
     await user.selectOptions(screen.getByLabelText('Voice'), 'alloy')

     // User generates audio
     await user.click(screen.getByRole('button', { name: 'Generate Audio' }))

     // User sees success feedback
     await screen.findByText('Audio generated successfully')
   })
   ```

### Performance Tips for Test Suites

1. **Batch Related Tests**

   ```typescript
   describe('Provider Selection', () => {
     // Setup once for all tests in this suite
     beforeEach(() => {
       server.use(...commonHandlers);
     });

     // Related tests that can share setup
     it('should load providers');
     it('should handle provider selection');
     it('should update voices when provider changes');
   });
   ```

2. **Use Selective Queries**

   ```typescript
   // Slow: Searches entire document
   screen.getByText('Submit');

   // Fast: Searches within scope
   within(form).getByRole('button', { name: 'Submit' });
   ```

3. **Minimize Unnecessary Waits**

   ```typescript
   // Bad: Always waits full timeout
   await waitFor(() => expect(element).toBeInTheDocument(), { timeout: 3000 });

   // Good: Returns as soon as condition met
   await screen.findByText('Loaded');
   ```

### Real-World Testing Patterns

1. **Testing Without All Data**

   ```typescript
   // When API returns partial data during development
   it('should handle incomplete voice data gracefully', async () => {
     server.use(
       http.get('/api/voice-library/*', () => {
         return HttpResponse.json({
           voices: [{ id: 'voice1' /* missing name */ }]
         })
       })
     )

     render(<VoiceSelector />)

     // Should show what data is available
     await screen.findByText('voice1')
     // Should not crash due to missing fields
   })
   ```

2. **Testing Feature Flags**

   ```typescript
   it('should hide experimental features by default', () => {
     render(<App />)
     expect(screen.queryByText('Experimental Feature')).not.toBeInTheDocument()
   })

   it('should show experimental features when enabled', () => {
     render(<App />, {
       preloadedState: { featureFlags: { experimental: true } }
     })
     expect(screen.getByText('Experimental Feature')).toBeInTheDocument()
   })
   ```

## Resources

- [Vitest Documentation](https://vitest.dev/)
- [Testing Library Docs](https://testing-library.com/docs/react-testing-library/intro/)
- [MSW Documentation](https://mswjs.io/)
- [Testing Playground](https://testing-playground.com/)
- [Common Testing Library Mistakes](https://kentcdodds.com/blog/common-mistakes-with-react-testing-library)
- [ADR-0003: Testing Approach](../../../../output/docs/adr/0003-testing-approach.md)
