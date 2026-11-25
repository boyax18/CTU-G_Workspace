import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { ApiError } from '../../api/client';
import { getHelpArticles, submitHelpRequest } from './api';
import type { HelpArticle } from './api';

export default function HelpPage() {
  const [articles, setArticles] = useState<HelpArticle[]>([]);
  const [category, setCategory] = useState('');
  const [subject, setSubject] = useState('');
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getHelpArticles(category)
      .then((result) => { if (!cancelled) setArticles(result); })
      .catch((caught) => {
        if (!cancelled) setError(caught instanceof ApiError ? caught.message : 'Unable to load help articles.');
      })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [category]);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError('');
    setSuccess('');
    if (!subject.trim() || !message.trim()) {
      setError('Subject and message are required.');
      return;
    }
    setSubmitting(true);
    try {
      await submitHelpRequest(subject.trim(), message.trim());
      setSubject('');
      setMessage('');
      setSuccess('Your message was sent to the Admin Office.');
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Unable to send your message.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {error && <div className="dashboard-panel rounded-xl border px-4 py-3 text-sm" role="alert">{error}</div>}
      {success && <div className="dashboard-panel rounded-xl border px-4 py-3 text-sm" role="status">{success}</div>}
      <section className="dashboard-panel rounded-2xl border p-5 sm:p-6">
        <h2 className="dashboard-heading text-lg font-semibold">Student Assistant</h2>
        <label className="dashboard-heading mt-4 block text-sm font-medium">
          Category
          <select className="mt-2 w-full rounded-lg border px-3 py-2" value={category} onChange={(event) => setCategory(event.target.value)}>
            <option value="">All categories</option>
            <option value="Finance">Finance</option>
            <option value="Clearance">Clearance</option>
            <option value="Account">Account</option>
          </select>
        </label>
        {loading ? (
          <p className="dashboard-muted mt-4 text-sm" role="status">Loading help articles...</p>
        ) : articles.length === 0 ? (
          <p className="dashboard-muted mt-4 text-sm">No help articles are available.</p>
        ) : (
          <div className="mt-4 space-y-3">
            {articles.map((article) => (
              <details key={article.id} className="rounded-xl border p-4">
                <summary className="dashboard-heading cursor-pointer font-semibold">{article.question}</summary>
                <p className="dashboard-muted mt-3 whitespace-pre-line text-sm leading-relaxed">{article.answer}</p>
              </details>
            ))}
          </div>
        )}
      </section>
      <section className="dashboard-panel rounded-2xl border p-5 sm:p-6">
        <h2 className="dashboard-heading text-lg font-semibold">Contact the Admin Office</h2>
        <form className="mt-4 space-y-4" onSubmit={submit} noValidate>
          <label className="dashboard-heading block text-sm font-medium">
            Subject
            <input className="mt-2 w-full rounded-lg border px-3 py-2" maxLength={150} value={subject}
              onChange={(event) => setSubject(event.target.value)} />
          </label>
          <label className="dashboard-heading block text-sm font-medium">
            Message
            <textarea className="mt-2 min-h-32 w-full rounded-lg border px-3 py-2" maxLength={2000} value={message}
              onChange={(event) => setMessage(event.target.value)} />
          </label>
          <button type="submit" disabled={submitting} className="rounded-lg bg-green-700 px-5 py-2 text-sm font-semibold text-white disabled:opacity-50">
            {submitting ? 'Sending...' : 'Send message'}
          </button>
        </form>
      </section>
    </div>
  );
}
