import { Link, useRouterState } from '@tanstack/react-router';
import { FileText, Home, Mic, Play, Settings, Users } from 'lucide-react';
import React from 'react';

import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { useProjectStatus } from '@/hooks/queries/useProjectStatus';
import { getNavigationItemClassName } from '@/lib/navigation-styles';
import { cn } from '@/lib/utils';
import { useHasProject, useProject } from '@/stores/appStore';

interface NavigationItem {
  label: string;
  to: string;
  icon: React.ComponentType<{ className?: string }>;
  enabled: boolean;
  tooltip?: string;
  activePathPrefixes?: string[];
  matchStrategy?: 'exact' | 'prefix';
}

interface NavigationSection {
  title: string;
  items: NavigationItem[];
}

interface ProjectModeNavigationProps {
  isExpanded?: boolean;
  className?: string;
}

export function ProjectModeNavigation({
  isExpanded = true,
  className,
}: ProjectModeNavigationProps) {
  const hasProject = useHasProject();
  const { mode, project } = useProject();
  const projectInputPath =
    mode === 'project' && project ? project.inputPath : undefined;
  const { status } = useProjectStatus(projectInputPath);

  // Centralized helper: Determine if an item should be disabled
  const shouldDisableItem = (item: NavigationItem): boolean => {
    // If no project loaded, disable everything except Overview
    if (!hasProject && item.to !== '/project') {
      return true;
    }

    // Otherwise use the item's own enabled status
    return !item.enabled;
  };

  // Centralized helper: Get tooltip text for disabled items
  const getDisabledTooltip = (item: NavigationItem): string | undefined => {
    // If no project loaded and not Overview
    if (!hasProject && item.to !== '/project') {
      return 'Select or create a project first';
    }

    // Otherwise use the item's own tooltip
    return item.tooltip;
  };

  const sections: NavigationSection[] = [
    {
      title: 'Setup',
      items: [
        {
          label: 'Overview',
          to: '/project',
          icon: Home,
          enabled: true,
          matchStrategy: 'exact',
        },
        {
          label: 'Screenplay Info',
          to: '/project/screenplay',
          icon: FileText,
          enabled: status?.hasJson ?? false,
          tooltip: !status?.hasJson ? 'Parse screenplay first' : undefined,
        },
      ],
    },
    {
      title: 'Configuration',
      items: [
        {
          label: 'Cast Voices',
          to: '/project/voices',
          icon: Users,
          enabled: status?.hasJson ?? false,
          tooltip: !status?.hasJson ? 'Parse screenplay first' : undefined,
          activePathPrefixes: ['/voice-casting'],
        },
        {
          label: 'Test Voices',
          to: '/project/test',
          icon: Play,
          enabled: true,
        },
        {
          label: 'Text Processing',
          to: '/project/processing',
          icon: Settings,
          enabled: false,
          tooltip: 'Feature coming in future release',
        },
      ],
    },
    {
      title: 'Generation',
      items: [
        {
          label: 'Generate Audio',
          to: '/project/generate',
          icon: Mic,
          enabled: status?.voicesCast ?? false,
          tooltip: !status?.voicesCast ? 'Cast voices first' : undefined,
        },
      ],
    },
  ];

  // Apply centralized disable logic to all sections
  const sectionsWithDisableLogic: NavigationSection[] = sections.map(
    (section) => ({
      ...section,
      items: section.items.map((item) => ({
        ...item,
        enabled: !shouldDisableItem(item),
        tooltip: shouldDisableItem(item)
          ? getDisabledTooltip(item)
          : item.tooltip,
      })),
    })
  );

  return (
    <div className={cn('space-y-4', className)}>
      {sectionsWithDisableLogic.map((section) => (
        <NavigationSection
          key={section.title}
          section={section}
          isExpanded={isExpanded}
        />
      ))}
    </div>
  );
}

interface NavigationSectionProps {
  section: NavigationSection;
  isExpanded: boolean;
}

function NavigationSection({ section, isExpanded }: NavigationSectionProps) {
  return (
    <div>
      {/* Section Header */}
      {isExpanded && (
        <div className="text-muted-foreground px-3 py-2 text-xs font-semibold tracking-wide uppercase">
          {section.title}
        </div>
      )}

      {/* Navigation Items */}
      <div className="space-y-1">
        {section.items.map((item) => (
          <NavigationItem
            key={item.label}
            item={item}
            isExpanded={isExpanded}
          />
        ))}
      </div>
    </div>
  );
}

interface NavigationItemProps {
  item: NavigationItem;
  isExpanded: boolean;
}

function NavigationItem({ item, isExpanded }: NavigationItemProps) {
  const pathname = useRouterState({
    select: (state) => state.location.pathname,
  });
  const matchesPath = (
    path: string,
    target: string,
    strategy: 'exact' | 'prefix'
  ) =>
    strategy === 'exact'
      ? path === target
      : path === target || path.startsWith(`${target}/`);

  const strategy = item.matchStrategy ?? 'prefix';
  const matchesPrimary = matchesPath(pathname, item.to, strategy);
  const matchesAdditional =
    item.activePathPrefixes?.some((prefix) =>
      matchesPath(pathname, prefix, 'prefix')
    ) ?? false;
  const isActive = matchesPrimary || matchesAdditional;
  const IconComponent = item.icon;

  const content = (
    <Link
      to={item.to}
      className={getNavigationItemClassName({
        isActive,
        isDisabled: !item.enabled,
        isCollapsed: !isExpanded,
      })}
      onClick={!item.enabled ? (e) => e.preventDefault() : undefined}
      aria-disabled={!item.enabled}
      aria-label={
        !item.enabled
          ? `${item.label} - ${item.tooltip || 'Not available yet'}`
          : item.label
      }
      aria-current={isActive ? 'page' : undefined}
    >
      <IconComponent className="h-4 w-4 flex-shrink-0" />
      {isExpanded && (
        <div className="flex flex-1 items-center justify-between">
          <span className="overflow-hidden whitespace-nowrap">
            {item.label}
          </span>
        </div>
      )}
    </Link>
  );

  // Wrap with tooltip for disabled items or when collapsed
  if ((!item.enabled && item.tooltip) || (!isExpanded && item.enabled)) {
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>{content}</TooltipTrigger>
          <TooltipContent side="right">
            <p>{item.tooltip || item.label}</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  }

  return content;
}
