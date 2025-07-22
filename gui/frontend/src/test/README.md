# Frontend Testing Guide

This guide covers testing patterns, conventions, and best practices for the Script-to-Speech frontend.

## Quick Start

```bash
# Run all tests
pnpm test

# Run tests in watch mode
pnpm test:watch

# Run tests with coverage
pnpm test:coverage

# Open the Vitest UI
pnpm test:ui
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
import userEvent from '@testing-library/user-event'

const user = userEvent.setup()

// Click
await user.click(button)

// Type
await user.type(input, 'Hello')

// Select
await user.selectOptions(select, 'option-value')

// Keyboard
await user.keyboard('{Enter}')
```

### Async Operations

Use `findBy` queries and `waitFor` for async operations:

```typescript
// Wait for element to appear
const element = await screen.findByText('Loaded')

// Wait for assertion
await waitFor(() => {
  expect(mockFn).toHaveBeenCalled()
})

// Wait with custom timeout
await screen.findByText('Loaded', { timeout: 3000 })
```

### API Mocking

We use MSW (Mock Service Worker) for API mocking:

```typescript
import { http, HttpResponse } from 'msw'
import { server } from '@/test/mocks/server'

// Override handler for specific test
server.use(
  http.get('/api/providers/info', () => {
    return HttpResponse.json({ error: 'Server error' }, { status: 500 })
  })
)

// Reset handlers after test
afterEach(() => {
  server.resetHandlers()
})
```

### Store Testing

Test stores in isolation with fresh instances:

```typescript
import { createTestStore } from '@/test/utils/createStore'

it('should update provider', () => {
  // Arrange
  const store = createTestStore()
  
  // Act
  store.getState().setSelectedProvider('elevenlabs')
  
  // Assert
  expect(store.getState().selectedProvider).toBe('elevenlabs')
})
```

### Hook Testing

Use `renderHook` with our custom wrapper:

```typescript
import { renderHook, waitFor } from '@/test/utils/render'

const { result } = renderHook(() => useProviders())

await waitFor(() => {
  expect(result.current.data).toBeDefined()
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

## Common Queries

Prefer accessible queries in this order:

1. **ByRole**: `screen.getByRole('button', { name: 'Submit' })`
2. **ByLabelText**: `screen.getByLabelText('Email')`
3. **ByPlaceholderText**: `screen.getByPlaceholderText('Enter email')`
4. **ByText**: `screen.getByText('Welcome')`
5. **ByTestId**: `screen.getByTestId('custom-element')` (last resort)

## Testing Library Queries Reference

| Query Type | When to Use | Example |
|------------|-------------|---------|
| `getBy*` | Element exists | `getByRole('button')` |
| `queryBy*` | Element may not exist | `queryByText('Error')` |
| `findBy*` | Element appears async | `await findByText('Loaded')` |
| `getAllBy*` | Multiple elements | `getAllByRole('listitem')` |

## Mocking Best Practices

### Mock at the Network Boundary

```typescript
// Good: Mock API responses with MSW
http.get('/api/data', () => HttpResponse.json({ data }))

// Avoid: Mocking modules directly
vi.mock('@/services/api')
```

### Keep Mocks Minimal

```typescript
// Good: Mock only what the component uses
const mockAudio = {
  play: vi.fn(() => Promise.resolve()),
  pause: vi.fn(),
  currentTime: 0,
  duration: 120
}

// Avoid: Complete interface mocks when unnecessary
```

### Test Data Factories

Use factories for consistent test data:

```typescript
import { createMockProvider, createMockTask } from '@/test/utils/test-data'

const provider = createMockProvider({ name: 'openai' })
const task = createMockTask({ status: 'completed' })
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
screen.debug()

// Print specific element
screen.debug(screen.getByRole('button'))

// Log queries available
screen.logTestingPlaygroundURL()
```

### Common Issues

#### "Not wrapped in act(...)"

This usually means a state update happened after the test finished:

```typescript
// Fix: Wait for all updates to complete
await waitFor(() => {
  expect(screen.getByText('Updated')).toBeInTheDocument()
})
```

#### "Unable to find element"

Check the query and use `screen.debug()`:

```typescript
// Debug what's rendered
screen.debug()

// Use more specific queries
screen.getByRole('button', { name: 'Specific Button' })
```

#### Test Timeouts

Increase timeout for specific tests:

```typescript
it('should handle slow operations', async () => {
  // test code
}, 10000) // 10 second timeout
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

## Resources

- [Vitest Documentation](https://vitest.dev/)
- [Testing Library Docs](https://testing-library.com/docs/react-testing-library/intro/)
- [MSW Documentation](https://mswjs.io/)
- [Testing Playground](https://testing-playground.com/)