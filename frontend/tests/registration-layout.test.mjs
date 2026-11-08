import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { registerHooks } from 'node:module';
import { test } from 'node:test';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import ts from 'typescript';

// Load the actual TSX components with the existing compiler. No DOM emulation,
// additional dependencies, generated source files, or backend requests are used.
const hooks = registerHooks({
  resolve(specifier, context, nextResolve) {
    if (specifier.startsWith('.') && context.parentURL) {
      for (const extension of ['.tsx', '.ts']) {
        const candidate = new URL(specifier + extension, context.parentURL);
        if (existsSync(candidate)) return nextResolve(candidate.href, context);
      }
    }
    return nextResolve(specifier, context);
  },
  load(url, context, nextLoad) {
    if (/\.tsx?$/.test(url)) {
      const { outputText } = ts.transpileModule(readFileSync(new URL(url), 'utf8'), {
        fileName: new URL(url).pathname,
        compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ESNext, jsx: ts.JsxEmit.ReactJSX },
      });
      return { format: 'module', source: outputText, shortCircuit: true };
    }
    return nextLoad(url, context);
  },
});

const { default: RegisterPage } = await import('../src/features/auth/RegisterPage.tsx');
const { default: SchoolInformation } = await import('../src/features/auth/RegistrationSchoolInformation.tsx');
hooks.deregister();

test('actual registration page places Register as before three ordered sections', () => {
  const html = renderToStaticMarkup(createElement(RegisterPage));
  assert.match(html, />Create Account<\/h1>/);
  assert.ok(html.includes('Create your CTU-G Workspace account. Student and Instructor registrations require administrative approval.'));
  const sections = ['Register as', '01 — Login Credentials', '02 — Personal Information', '03 — School Information'];
  const positions = sections.map((text) => html.indexOf(text));
  assert.ok(positions.every((position) => position >= 0));
  assert.deepEqual(positions, [...positions].sort((a, b) => a - b));
  assert.equal((html.match(/<form\b/g) || []).length, 1);
  assert.match(html, />Submit Registration<\/button>/);
  assert.match(html, />Back to Home<\/a>/);
});

test('credentials and personal information retain their required fields and two-column desktop groups', () => {
  const html = renderToStaticMarkup(createElement(RegisterPage));
  const credentials = html.slice(html.indexOf('01 — Login Credentials'), html.indexOf('02 — Personal Information'));
  const personal = html.slice(html.indexOf('02 — Personal Information'), html.indexOf('03 — School Information'));
  for (const field of ['school_id', 'email', 'password', 'password_confirmation']) assert.ok(credentials.includes(`name="${field}"`));
  for (const field of ['first_name', 'last_name', 'middle_name', 'suffix']) assert.ok(personal.includes(`name="${field}"`));
  for (const field of ['school_id', 'password', 'password_confirmation', 'first_name', 'last_name']) {
    const input = html.match(new RegExp(`<input[^>]*name="${field}"[^>]*>`))[0];
    assert.ok(input.includes('required=""'), `${field} must be required`);
  }
  for (const field of ['email', 'middle_name', 'suffix']) {
    const input = html.match(new RegExp(`<input[^>]*name="${field}"[^>]*>`))[0];
    assert.ok(!input.includes('required='));
  }
  assert.ok(credentials.includes('grid gap-4 sm:grid-cols-2'));
  assert.ok(personal.includes('grid gap-4 sm:grid-cols-2'));
});

test('role selector offers only Student and Instructor; password controls are labelled non-submit buttons', () => {
  const html = renderToStaticMarkup(createElement(RegisterPage));
  assert.equal((html.match(/<option\b/g) || []).length, 2);
  assert.match(html, /<option value="Student" selected="">Student<\/option>/);
  assert.match(html, /<option value="Instructor">Instructor<\/option>/);
  for (const label of ['Show password', 'Show confirm password']) {
    assert.match(html, new RegExp(`<button type="button" aria-label="${label}" aria-pressed="false"`));
  }
  assert.equal((html.match(/type="password"/g) || []).length, 2);
});

test('Student school information is a non-interactive preview without fabricated values or payload fields', () => {
  const html = renderToStaticMarkup(createElement(SchoolInformation, { role: 'Student' }));
  for (const label of ['Course', 'Year Level', 'Section']) assert.ok(html.includes(label));
  assert.match(html, /not collected during registration/);
  assert.equal((html.match(/Configured later/g) || []).length, 3);
  assert.doesNotMatch(html, /<(input|select|textarea|button)\b/);
  assert.match(html, /aria-live="polite"/);
});

test('Instructor school information shows only the after-approval assignment message', () => {
  const html = renderToStaticMarkup(createElement(SchoolInformation, { role: 'Instructor' }));
  assert.ok(html.includes('Instructor academic and teaching assignments will be configured after account approval.'));
  assert.doesNotMatch(html, /<dt>|<(input|select|textarea)\b|Configured later/);
});
