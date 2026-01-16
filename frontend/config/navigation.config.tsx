import { Home, User, Wrench, Bot, BarChart3, Package, Users, FileText, FolderSync, AlertTriangle, BookOpen, Sparkles, BrainCircuit } from 'lucide-react';
import { z } from 'zod';

import { NavigationConfigSchema } from '@kit/ui/navigation-schema';

import pathsConfig from '~/config/paths.config';

const iconClasses = 'w-4';

const routes = [
  {
    label: 'common:routes.application',
    children: [
      {
        label: 'common:routes.home',
        path: pathsConfig.app.home,
        Icon: <Home className={iconClasses} />,
        end: true,
      },
      {
        label: 'KPI Analytics',
        path: pathsConfig.app.kpi,
        Icon: <BarChart3 className={iconClasses} />,
        allowedRoles: ['admin', 'supervisor', 'viewer'],
      },
      {
        label: 'AMDEC / RPN',
        path: pathsConfig.app.amdec,
        Icon: <AlertTriangle className={iconClasses} />,
        allowedRoles: ['admin', 'supervisor'],
      },
      {
        label: 'Training Priority',
        path: pathsConfig.app.priorityTraining,
        Icon: <BookOpen className={iconClasses} />,
        allowedRoles: ['admin', 'supervisor'],
      },
      {
        label: 'Knowledge Base',
        path: pathsConfig.app.knowledgeBase,
        Icon: <FileText className={iconClasses} />,
      },
      {
        label: 'Equipment',
        path: pathsConfig.app.equipment,
        Icon: <Wrench className={iconClasses} />,
      },
      {
        label: 'Interventions',
        path: pathsConfig.app.interventions,
        Icon: <Wrench className={iconClasses} />,
      },
      {
        label: 'Log Intervention',
        path: pathsConfig.app.newIntervention,
        Icon: <Sparkles className={iconClasses} />,
        allowedRoles: ['technician'],
      },
      {
        label: 'Spare Parts',
        path: pathsConfig.app.spareParts,
        Icon: <Package className={iconClasses} />,
      },
      {
        label: 'Technicians',
        path: pathsConfig.app.technicians,
        Icon: <Users className={iconClasses} />,
        allowedRoles: ['admin'],
      },
    ],
  },
  {
    label: 'Tools',
    children: [
      {
        label: 'Copilot',
        path: pathsConfig.app.copilot,
        Icon: <Sparkles className={iconClasses} />,
      },
      {
        label: 'AI Forecast',
        path: pathsConfig.app.aiForecast,
        Icon: <BrainCircuit className={iconClasses} />,
        allowedRoles: ['admin', 'supervisor', 'viewer'],
      },
      {
        label: 'AI Assistant',
        path: pathsConfig.app.assistant,
        Icon: <Bot className={iconClasses} />,
      },
      {
        label: 'OCR Scanner',
        path: pathsConfig.app.ocr,
        Icon: <FileText className={iconClasses} />,
      },
      {
        label: 'Import / Export',
        path: pathsConfig.app.importExport,
        Icon: <FolderSync className={iconClasses} />,
        allowedRoles: ['admin', 'supervisor'],
      },
    ],
  },
  {
    label: 'common:routes.settings',
    children: [
      {
        label: 'common:routes.profile',
        path: pathsConfig.app.profileSettings,
        Icon: <User className={iconClasses} />,
      },
    ],
  },
] satisfies z.infer<typeof NavigationConfigSchema>['routes'];

export const navigationConfig = NavigationConfigSchema.parse({
  routes,
  style: process.env.NEXT_PUBLIC_NAVIGATION_STYLE,
  sidebarCollapsed: process.env.NEXT_PUBLIC_HOME_SIDEBAR_COLLAPSED,
});
