import { Bot, Building2, Globe, Mic, Settings, Sparkles } from 'lucide-react';

// Dynamically import provider logos
// The logo files should be placed in /src/assets/providers/ with naming convention: {provider}-logo.{ext}
const logoModules = import.meta.glob<{ default: string }>(
  '/src/assets/providers/*-logo.{svg,png,jpg,jpeg,webp}',
  { eager: true }
);

// Pre-compute all provider logos at module initialization
const providerLogos: Record<string, string | undefined> = {};

// Build the logo map once
for (const [path, module] of Object.entries(logoModules)) {
  // Extract provider name from path like /src/assets/providers/openai-logo.svg
  const match = path.match(/\/([^/]+)-logo\.\w+$/);
  if (match) {
    const provider = match[1];
    providerLogos[provider] = module.default;
  }
}

export const PROVIDER_META = {
  openai: {
    icon: Sparkles,
    name: 'OpenAI',
    bgColor: 'bg-emerald-100',
    iconColor: 'text-emerald-700',
    fallback: 'OA',
    logo: providerLogos['openai'],
  },
  elevenlabs: {
    icon: Mic,
    name: 'ElevenLabs',
    bgColor: 'bg-purple-100',
    iconColor: 'text-purple-700',
    fallback: 'EL',
    logo: providerLogos['elevenlabs'],
  },
  cartesia: {
    icon: Bot,
    name: 'Cartesia',
    bgColor: 'bg-blue-100',
    iconColor: 'text-blue-700',
    fallback: 'CA',
    logo: providerLogos['cartesia'],
  },
  zonos: {
    icon: Globe,
    name: 'Zonos',
    bgColor: 'bg-teal-100',
    iconColor: 'text-teal-700',
    fallback: 'ZO',
    logo: providerLogos['zonos'],
  },
  minimax: {
    icon: Building2,
    name: 'MiniMax',
    bgColor: 'bg-pink-100',
    iconColor: 'text-pink-700',
    fallback: 'MM',
    logo: providerLogos['minimax'],
  },
} as const;

export const DEFAULT_PROVIDER_META = {
  icon: Settings,
  name: 'Custom Provider',
  bgColor: 'bg-gray-100',
  iconColor: 'text-gray-700',
  fallback: '??',
  logo: undefined,
} as const;

export function getProviderMeta(provider: string) {
  return (
    PROVIDER_META[provider as keyof typeof PROVIDER_META] ||
    DEFAULT_PROVIDER_META
  );
}
