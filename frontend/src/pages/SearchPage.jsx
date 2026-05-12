import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';

const COLS = [
  { key: 'video_name', label: 'Video Name' },
  { key: 'institution', label: 'Institution' },
  { key: 'procedure', label: 'Procedure' },
  { key: 'anon_status', label: 'Anon Status' },
  { key: 'length', label: 'Frames' },
  { key: 'fps', label: 'FPS' },
  { key: 'annotation_status', label: 'Annotation' },
];

function Badge({ value }) {
  const colors = {
    anonymized: 'bg-green-100 text-green-700',
    raw: 'bg-yellow-100 text-yellow-700',
    missing: 'bg-red-100 text-red-700',
    Annotated: 'bg-blue-100 text-blue-700',
    Untagged: 'bg-slate-100 text-slate-600',
  };
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${colors[value] ?? 'bg-slate-100 text-slate-600'}`}>
      {value ?? '—'}
    </span>
  );
}

export default function SearchPage() {
  const navigate = useNavigate();
  const [options, setOptions] = useState({});
  const [filters, setFilters] = useState({ institution: '', procedure: '', anon_status: '', annotation_status: '', search: '', limit: 100, offset: 0 });
  const [results, setResults] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    api.getOptions().then(setOptions).catch(() => {});
  }, []);

  const search = useCallback(() => {
    setLoading(true);
    setError('');
    api.listVideos(filters)
      .then(({ total, results }) => { setTotal(total); setResults(results); })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [filters]);

  useEffect(() => { search(); }, [search]);

  const set = (key, val) => setFilters(f => ({ ...f, [key]: val, offset: 0 }));

  return (
    <div className="space-y-4">
      <div className="bg-white rounded-xl border border-slate-200 p-4">
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          <input
            className="col-span-2 lg:col-span-2 border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
            placeholder="Search name, path, institution…"
            value={filters.search}
            onChange={e => set('search', e.target.value)}
          />
          {[['institution', 'Institution'], ['procedure', 'Procedure'], ['anon_status', 'Anon Status'], ['annotation_status', 'Annotation']].map(([key, label]) => (
            <select
              key={key}
              className="border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 bg-white"
              value={filters[key]}
              onChange={e => set(key, e.target.value)}
            >
              <option value="">{label}</option>
              {(options[key === 'anon_status' ? 'anon_status' : key === 'annotation_status' ? 'annotation_status' : key + 's'] ?? []).map(v => (
                <option key={v} value={v}>{v}</option>
              ))}
            </select>
          ))}
        </div>
      </div>

      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-500">
          {loading ? 'Loading…' : `${total.toLocaleString()} video${total !== 1 ? 's' : ''}`}
        </p>
        {error && <p className="text-sm text-red-500">{error}</p>}
      </div>

      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100 bg-slate-50">
              {COLS.map(c => (
                <th key={c.key} className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">
                  {c.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {results.map(row => (
              <tr
                key={row.video_id}
                className="hover:bg-slate-50 cursor-pointer transition-colors"
                onClick={() => navigate(`/videos/${row.video_id}`)}
              >
                <td className="px-4 py-3 font-mono text-xs text-slate-700">{row.video_name}</td>
                <td className="px-4 py-3 text-slate-600">{row.institution ?? '—'}</td>
                <td className="px-4 py-3 text-slate-600">{row.procedure ?? '—'}</td>
                <td className="px-4 py-3"><Badge value={row.anon_status} /></td>
                <td className="px-4 py-3 text-slate-500">{row.length?.toLocaleString() ?? '—'}</td>
                <td className="px-4 py-3 text-slate-500">{row.fps ?? '—'}</td>
                <td className="px-4 py-3"><Badge value={row.annotation_status} /></td>
              </tr>
            ))}
            {!loading && results.length === 0 && (
              <tr><td colSpan={7} className="px-4 py-10 text-center text-slate-400">No results</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {total > filters.limit && (
        <div className="flex justify-center gap-2">
          <button
            disabled={filters.offset === 0}
            onClick={() => setFilters(f => ({ ...f, offset: Math.max(0, f.offset - f.limit) }))}
            className="px-4 py-2 text-sm border border-slate-200 rounded-lg disabled:opacity-40 hover:bg-slate-100"
          >
            Previous
          </button>
          <span className="px-4 py-2 text-sm text-slate-500">
            {filters.offset + 1}–{Math.min(filters.offset + filters.limit, total)} of {total}
          </span>
          <button
            disabled={filters.offset + filters.limit >= total}
            onClick={() => setFilters(f => ({ ...f, offset: f.offset + f.limit }))}
            className="px-4 py-2 text-sm border border-slate-200 rounded-lg disabled:opacity-40 hover:bg-slate-100"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
