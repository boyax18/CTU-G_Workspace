/** Academic settings: courses, subjects, sections, curriculum versions, offerings and instructors.
 *
 * Tabs appear only for the exact permission codes the session reports (presentation only); Django
 * re-checks the exact code, Admin role context and Deny precedence on every request. Curriculum,
 * offering and instructor-assignment writes also need their own server switches and build flags.
 */
import { useId, useRef, useState } from 'react';
import type { KeyboardEvent } from 'react';
import { useDashboardContext } from '../../hooks/useDashboardContext';
import { AREA_CODES } from './academicConfigurationConfig.ts';
import CurriculaTab from './config/CurriculaTab.tsx';
import { CoursesTab, SectionsTab, SubjectsTab } from './config/DefinitionTabs.tsx';
import OfferingsTab from './config/OfferingsTab.tsx';
import { ring } from './academicStyles.ts';

type TabId = 'courses' | 'subjects' | 'sections' | 'curricula' | 'offerings';
const TABS: { id: TabId; label: string; codes: readonly string[] }[] = [
  { id: 'courses', label: 'Courses', codes: [AREA_CODES.courses] },
  { id: 'subjects', label: 'Subjects', codes: [AREA_CODES.subjects] },
  { id: 'sections', label: 'Sections', codes: [AREA_CODES.sections] },
  { id: 'curricula', label: 'Curriculum versions', codes: [AREA_CODES.curricula] },
  { id: 'offerings', label: 'Offerings & instructors', codes: [AREA_CODES.offerings, AREA_CODES.teaching] },
];

export default function AcademicSettingsPanel() {
  const ids = useId();
  const { session } = useDashboardContext();
  const grants = new Set(session.permissions);
  const visible = TABS.filter((tab) => tab.codes.some((code) => grants.has(code)));
  const [active, setActive] = useState<TabId | null>(visible[0]?.id ?? null);
  const refs = useRef<Record<string, HTMLButtonElement | null>>({});

  if (!active || visible.length === 0) {
    return (
      <section className="dashboard-panel rounded-2xl border p-6">
        <h2 className="dashboard-heading text-lg font-semibold">No academic settings are available to you</h2>
        <p className="dashboard-muted mt-2 text-sm">Your current access does not include an academic configuration permission.</p>
      </section>
    );
  }

  function onKey(event: KeyboardEvent<HTMLDivElement>) {
    const index = visible.findIndex((t) => t.id === active);
    const next = event.key === 'ArrowRight' ? (index + 1) % visible.length
      : event.key === 'ArrowLeft' ? (index - 1 + visible.length) % visible.length
        : event.key === 'Home' ? 0 : event.key === 'End' ? visible.length - 1 : -1;
    if (next < 0) return;
    event.preventDefault();
    setActive(visible[next].id);
    refs.current[visible[next].id]?.focus();
  }

  const canOfferings = grants.has(AREA_CODES.offerings);
  return (
    <div className="space-y-4">
      <p className="dashboard-muted text-sm">
        These are CTU-G Workspace configuration records for semester activation and student onboarding. They do not change or
        prove official CTU enrollment.
      </p>
      <div role="tablist" aria-label="Academic settings" onKeyDown={onKey} className="flex flex-wrap gap-2 border-b pb-2">
        {visible.map((tab) => (
          <button key={tab.id} ref={(node) => { refs.current[tab.id] = node; }} type="button" role="tab" id={`${ids}-${tab.id}`}
            aria-selected={active === tab.id} aria-controls={`${ids}-${tab.id}-panel`} tabIndex={active === tab.id ? 0 : -1}
            onClick={() => setActive(tab.id)}
            className={`min-h-11 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${ring} ${active === tab.id
              ? 'dashboard-primary-link' : 'dashboard-outline-button border'}`}>
            {tab.label}
          </button>
        ))}
      </div>
      <div role="tabpanel" id={`${ids}-${active}-panel`} aria-labelledby={`${ids}-${active}`}>
        {active === 'courses' && <CoursesTab canWrite />}
        {active === 'subjects' && <SubjectsTab canWrite />}
        {active === 'sections' && <SectionsTab canWrite />}
        {active === 'curricula' && <CurriculaTab canWrite />}
        {active === 'offerings' && (canOfferings
          ? <OfferingsTab canWriteOfferings canAssign={grants.has(AREA_CODES.teaching)} />
          : <p className="dashboard-muted text-sm">Offerings are listed for the academic-period permission. Ask a School Admin to check your access.</p>)}
      </div>
    </div>
  );
}
