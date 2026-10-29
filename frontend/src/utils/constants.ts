export const BRAND_NAME = 'CTU-G Workspace';
export const CAMPUS_NAME = 'Cebu Technological University – Ginatilan Campus';

/**
 * Registration entry point. Verify this matches the path registered for
 * RegisterPage in routes/AppRoutes.tsx. Set to null to hide registration links.
 */
export const REGISTER_PATH: string | null = '/register';

/** Page sections in order, used for scroll paging (one scroll gesture moves to the next one). */
export const PAGE_SECTION_IDS = [
  'home',
  'services',
  'how-it-works',
  'about',
  'announcements',
  'help',
  'contact',
] as const;
