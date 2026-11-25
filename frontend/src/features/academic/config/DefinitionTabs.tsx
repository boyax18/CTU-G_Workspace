/** Courses (academic.courses.manage), subjects (clearance.subjects.manage) and sections
 * (academic.sections.manage). Loaders are module-level so effects do not re-run on every render. */
import { useEffect, useState } from 'react';
import {
  createCourse, createSection, createSubject, listCourses, listSections, listSubjects, setCourseStatus,
  setSectionStatus, setSubjectStatus, updateCourse, updateSection, updateSubject,
} from '../academicConfigurationApi.ts';
import type { Course, Section, Subject } from '../academicConfigurationApi.ts';
import { DefinitionTab } from './configUi.tsx';
import { YEAR_LEVEL_OPTIONS, blankToNull, toInt } from './configHelpers.ts';
import type { FieldSpec } from './configUi.tsx';

const CODE_HINT = 'Letters, digits, spaces, dots, hyphens or slashes; saved in capitals.';
const loadCourses = (query: { q?: string; page?: number }) => listCourses(query);
const loadSubjects = (query: { q?: string; page?: number }) => listSubjects(query);
const loadSections = (query: { q?: string; page?: number }) => listSections({ page: query.page });

const inUseNote = (inUse: boolean, what: string) => (inUse ? `This record is already used, so its ${what} cannot change. History keeps the original.` : null);

export function CoursesTab({ canWrite }: { canWrite: boolean }) {
  const fields = (locked = false): FieldSpec[] => [
    { name: 'code', label: 'Course code', maxLength: 20, hint: CODE_HINT, locked },
    { name: 'name', label: 'Course name', maxLength: 150 },
  ];
  return (
    <DefinitionTab<Course> noun="course" title="Courses" canWrite={canWrite} searchLabel="Search code or name"
      description="Workspace course definitions. They do not change official CTU enrollment records."
      load={loadCourses} keyOf={(c) => c.course_id} labelOf={(c) => c.code} statusOf={(c) => c.status}
      versionOf={(c) => c.version}
      summary={(c) => (<>
        <p className="dashboard-heading text-sm font-semibold">{c.code}</p>
        <p className="dashboard-muted text-sm">{c.name}</p>
        <p className="dashboard-muted mt-1 text-xs">{c.references.curricula} curricula · {c.references.sections} sections · {c.references.offerings} offerings</p>
      </>)}
      createFields={fields()} editFields={(c) => fields(c.in_use)} lockedNote={(c) => inUseNote(c.in_use, 'code')}
      valuesOf={(c) => ({ code: c.code, name: c.name })}
      create={(v) => createCourse({ code: v.code ?? '', name: v.name ?? '' })}
      update={(c, v) => updateCourse(c.course_id, { code: v.code ?? '', name: v.name ?? '', expected_version: c.version })}
      setStatus={(c, status) => setCourseStatus(c.course_id, status, c.version)} />
  );
}

const units = (s: Subject) => [s.lecture_units && `${s.lecture_units} lecture`, s.lab_units && `${s.lab_units} lab`]
  .filter(Boolean).join(' · ') || 'Units not set';

export function SubjectsTab({ canWrite }: { canWrite: boolean }) {
  const fields = (locked = false): FieldSpec[] => [
    { name: 'code', label: 'Subject code', maxLength: 20, hint: CODE_HINT, locked },
    { name: 'title', label: 'Subject title', maxLength: 200, locked },
    { name: 'classification', label: 'Classification (optional)', maxLength: 60 },
    { name: 'lecture_units', label: 'Lecture units (optional)', maxLength: 4, inputMode: 'decimal', locked,
      hint: 'Enter only officially approved units, from 0 to 30.' },
    { name: 'lab_units', label: 'Laboratory units (optional)', maxLength: 4, inputMode: 'decimal', locked },
  ];
  const body = (v: Record<string, string>) => ({ code: v.code ?? '', title: v.title ?? '',
    classification: blankToNull(v.classification), lecture_units: blankToNull(v.lecture_units), lab_units: blankToNull(v.lab_units) });
  return (
    <DefinitionTab<Subject> noun="subject" title="Subjects" canWrite={canWrite} searchLabel="Search code or title"
      description="Reusable subject definitions. A subject used by a curriculum or offering keeps its code, title and units."
      load={loadSubjects} keyOf={(s) => s.subject_id} labelOf={(s) => s.code} statusOf={(s) => s.status}
      versionOf={(s) => s.version}
      summary={(s) => (<>
        <p className="dashboard-heading text-sm font-semibold">{s.code} <span className="font-normal">· {s.title}</span></p>
        <p className="dashboard-muted text-xs">{units(s)}{s.classification ? ` · ${s.classification}` : ''}</p>
        <p className="dashboard-muted mt-1 text-xs">{s.references.curriculum_entries} curriculum entries · {s.references.offerings} offerings</p>
      </>)}
      createFields={fields()} editFields={(s) => fields(s.in_use)}
      lockedNote={(s) => inUseNote(s.in_use, 'code, title and units')}
      valuesOf={(s) => ({ code: s.code, title: s.title, classification: s.classification ?? '',
        lecture_units: s.lecture_units ?? '', lab_units: s.lab_units ?? '' })}
      create={(v) => createSubject(body(v))}
      update={(s, v) => updateSubject(s.subject_id, { ...body(v), expected_version: s.version })}
      setStatus={(s, status) => setSubjectStatus(s.subject_id, status, s.version)} />
  );
}

export function SectionsTab({ canWrite }: { canWrite: boolean }) {
  const [courses, setCourses] = useState<Course[]>([]);
  useEffect(() => {
    let cancelled = false;
    listCourses({ status: 'Active' }).then((page) => { if (!cancelled) setCourses(page.results); }).catch(() => undefined);
    return () => { cancelled = true; };
  }, []);
  const courseOptions = courses.map((c) => ({ value: String(c.course_id), label: `${c.code} · ${c.name}` }));
  const fields = (locked = false, create = false): FieldSpec[] => [
    ...(create ? [{ name: 'course_id', label: 'Course', kind: 'select' as const, options: courseOptions }] : []),
    { name: 'year_level', label: 'Year level', kind: 'select', options: YEAR_LEVEL_OPTIONS, locked },
    { name: 'name', label: 'Section name', maxLength: 20, hint: 'For example, 1-A.', locked },
  ];
  return (
    <DefinitionTab<Section> noun="section" title="Sections" canWrite={canWrite}
      description="Sections by course and year level. A section with offerings keeps its name and year level."
      load={loadSections} keyOf={(s) => s.section_id} labelOf={(s) => `${s.course.code} ${s.name}`}
      statusOf={(s) => s.status} versionOf={(s) => s.version}
      summary={(s) => (<>
        <p className="dashboard-heading text-sm font-semibold">{s.course.code} · {s.name}</p>
        <p className="dashboard-muted text-xs">Year {s.year_level} · {s.references.offerings} offerings</p>
      </>)}
      createFields={fields(false, true)} editFields={(s) => fields(s.in_use)}
      lockedNote={(s) => inUseNote(s.in_use, 'name and year level')}
      valuesOf={(s) => ({ year_level: String(s.year_level), name: s.name })}
      create={(v) => createSection({ course_id: toInt(v.course_id), year_level: toInt(v.year_level), name: v.name ?? '' })}
      update={(s, v) => updateSection(s.section_id, { year_level: toInt(v.year_level), name: v.name ?? '', expected_version: s.version })}
      setStatus={(s, status) => setSectionStatus(s.section_id, status, s.version)} />
  );
}
