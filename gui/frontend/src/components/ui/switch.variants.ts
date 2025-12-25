import { cva } from 'class-variance-authority';

export const switchVariants = cva(
  'peer inline-flex shrink-0 cursor-pointer items-center rounded-full border-2 border-transparent shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:cursor-not-allowed disabled:opacity-50 data-[state=checked]:bg-zinc-900 data-[state=unchecked]:bg-zinc-400',
  {
    variants: {
      size: {
        default: 'h-5 w-9',
        sm: 'h-4 w-7',
        lg: 'h-6 w-11',
      },
    },
    defaultVariants: {
      size: 'default',
    },
  }
);

export const switchThumbVariants = cva(
  'pointer-events-none block rounded-full bg-white shadow-lg ring-1 ring-zinc-950/10 transition-transform',
  {
    variants: {
      size: {
        default:
          'h-4 w-4 data-[state=checked]:translate-x-4 data-[state=unchecked]:translate-x-0',
        sm: 'h-3 w-3 data-[state=checked]:translate-x-3 data-[state=unchecked]:translate-x-0',
        lg: 'h-5 w-5 data-[state=checked]:translate-x-5 data-[state=unchecked]:translate-x-0',
      },
    },
    defaultVariants: {
      size: 'default',
    },
  }
);
