# Provider Logos

Place provider logo files in this directory to replace the default letter avatars in the TTS interface.

## Supported Formats

- **SVG** (recommended) - Best quality at any size, smallest file size
- **PNG** - Good for detailed logos, supports transparency
- **JPG/JPEG** - For photographic logos without transparency needs
- **WebP** - Modern format with excellent compression

## Naming Convention

Files must follow this naming pattern: `{provider}-logo.{extension}`

### Examples:

- `openai-logo.svg`
- `elevenlabs-logo.png`
- `cartesia-logo.webp`
- `playht-logo.jpg`
- `minimax-logo.svg`

## Image Guidelines

### Dimensions

- **Minimum size**: 128x128px for raster formats (PNG, JPG, WebP)
- **Maximum size**: 512x512px (larger sizes will be scaled down)
- **Aspect ratio**: 1:1 (square) preferred, but other ratios will be handled

### Quality

- **File size**: Keep under 50KB when possible
- **Background**: Transparent background recommended for PNG/WebP
- **Colors**: Use high contrast for visibility on both light and dark themes

## Provider Identifiers

The following provider identifiers are currently supported:

- `openai` - OpenAI
- `elevenlabs` - ElevenLabs
- `cartesia` - Cartesia
- `playht` - PlayHT
- `minimax` - MiniMax

## Fallback Behavior

If no logo file is found for a provider, the system will fall back to:

1. A configured Lucide icon (if available)
2. The first letter of the provider name with a gradient background

## Adding New Logos

1. Add your logo file following the naming convention above
2. The logo will be automatically detected and used
3. No code changes required for standard providers

## Testing

After adding logos, you can test them by:

1. Running the development server: `make gui-dev`
2. Navigating to the TTS page
3. Opening the provider selection panel
