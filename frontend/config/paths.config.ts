import { z } from 'zod';

const PathsSchema = z.object({
  auth: z.object({
    signIn: z.string().min(1),
    signUp: z.string().min(1),
    verifyMfa: z.string().min(1),
    callback: z.string().min(1),
    passwordReset: z.string().min(1),
    passwordUpdate: z.string().min(1),
  }),
  app: z.object({
    home: z.string().min(1),
    profileSettings: z.string().min(1),
    equipment: z.string().min(1),
    interventions: z.string().min(1),
    assistant: z.string().min(1),
    kpi: z.string().min(1),
    spareParts: z.string().min(1),
    technicians: z.string().min(1),
    ocr: z.string().min(1),
    importExport: z.string().min(1),
    amdec: z.string().min(1),
    priorityTraining: z.string().min(1),
    knowledgeBase: z.string().min(1),
    copilot: z.string().min(1),
    newIntervention: z.string().min(1),
    aiForecast: z.string().min(1),
  }),
});

const pathsConfig = PathsSchema.parse({
  auth: {
    signIn: '/auth/sign-in',
    signUp: '/auth/sign-up',
    verifyMfa: '/auth/verify',
    callback: '/auth/callback',
    passwordReset: '/auth/password-reset',
    passwordUpdate: '/update-password',
  },
  app: {
    home: '/home',
    profileSettings: '/home/settings',
    equipment: '/home/equipment',
    interventions: '/home/interventions',
    newIntervention: '/home/interventions/new',
    assistant: '/home/assistant',
    kpi: '/home/kpi',
    spareParts: '/home/spare-parts',
    technicians: '/home/technicians',
    ocr: '/home/ocr',
    importExport: '/home/import-export',
    amdec: '/home/amdec',
    priorityTraining: '/home/priority-training',
    knowledgeBase: '/home/knowledge-base',
    copilot: '/home/copilot',
    aiForecast: '/home/ai-forecast',
  },
} satisfies z.infer<typeof PathsSchema>);

export default pathsConfig;
