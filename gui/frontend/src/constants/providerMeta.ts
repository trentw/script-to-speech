import { Bot, Building2, Globe, Mic, Settings, Sparkles } from 'lucide-react';

export const PROVIDER_META = {
  openai: {
    icon: Sparkles,
    name: 'OpenAI',
    bgColor: 'bg-emerald-100',
    iconColor: 'text-emerald-700',
    fallback: 'OA',
  },
  elevenlabs: {
    icon: Mic,
    name: 'ElevenLabs',
    bgColor: 'bg-purple-100',
    iconColor: 'text-purple-700',
    fallback: 'EL',
  },
  cartesia: {
    icon: Bot,
    name: 'Cartesia',
    bgColor: 'bg-blue-100',
    iconColor: 'text-blue-700',
    fallback: 'CA',
  },
  playht: {
    icon: Globe,
    name: 'PlayHT',
    bgColor: 'bg-orange-100',
    iconColor: 'text-orange-700',
    fallback: 'PH',
  },
  minimax: {
    icon: Building2,
    name: 'MiniMax',
    bgColor: 'bg-pink-100',
    iconColor: 'text-pink-700',
    fallback: 'MM',
  },
} as const;

export const DEFAULT_PROVIDER_META = {
  icon: Settings,
  name: 'Custom Provider',
  bgColor: 'bg-gray-100',
  iconColor: 'text-gray-700',
  fallback: '??',
} as const;

export function getProviderMeta(provider: string) {
  return (
    PROVIDER_META[provider as keyof typeof PROVIDER_META] ||
    DEFAULT_PROVIDER_META
  );
}
