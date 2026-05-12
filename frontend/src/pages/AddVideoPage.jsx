import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';

const FIELDS = [
  { key: 'video_name', label: 'Video Name', required: true },
  { key: 'video_path', label: 'Video Path', required: true, wide: true },
  { key: 'num_id', label: 'Numeric ID' },
  { key: 'video_ext', label: 'Extension', type: 'select', optKey: null, opts: ['mp4', 'avi', 'bmp'] },
  { key: 'institution', label: 'Institution', type: 'select', optKey: 'institutions' },
  { key: 'procedure', label: 'Procedure', type: 'select', optKey: 'procedures' },
  { key: 'anon_status', label: 'Anon Status', type: 'select', optKey: 'anon_status' },
  { key: 'storage_system', label: 'Storage System', type: 'select', optKey: 'storage_systems' },
  { key: 'length', label: 'Length (frames)' },
  { key: 'fps', label: 'FPS' },
  { key: 'date_recorded', label: 'Date Recorded', placeholder: 'YYYY-MM-DD' },
  { key: 'irb_protocol', label: 'IRB Protocol' },
  { key: 'surgical_approach', label: 'Surgical Approach', type: 'select', optKey: null, opts: ['Laparoscopic', 'Open', 'Robotic'] },
  { key: 'annotation_status', label: 'Annotation Status', type: 'select', optKey: 'annotation_status' },
  { key: 'notes', label: 'Notes', wide: true },
];

export default function AddVideoPage() {
  const navigate = useNavigate();
  const [options, setOptions] = useState({});
  const [form, setForm] = useState({ surgical_approach: 'Laparoscopic', annotation_status: 'Untagged', is_usable: 1 });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => { api.getOptions().then(setOptions).catch(() => {}); }, []);

  const set = (key, val) => setForm(f => ({ ...f, [key]: val }));

  const submit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    try {
      const { video_id } = await api.createVideo(form);
      navigate(`/videos/${video_id}`);
    } catch (e) {
      setError(e.message);
      setSaving(false);
    }
  };

  return (
    <div className="max-w-3xl space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Add Video Entry</h1>
        <p className="text-sm text-slate-500 mt-1">Manually add a single video to the database.</p>
      </div>

      {error && <p className="text-sm text-red-500 bg-red-50 px-4 py-2 rounded-lg">{error}</p>}

      <form onSubmit={submit} className="bg-white rounded-xl border border-slate-200 p-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {FIELDS.map(({ key, label, required, wide, type, optKey, opts, placeholder }) => {
            const fieldOpts = opts ?? (optKey ? options[optKey] : null);
            return (
              <div key={key} className={wide ? 'md:col-span-2' : ''}>
                <label className="block text-xs font-medium text-slate-500 mb-1">
                  {label} {required && <span className="text-red-400">*</span>}
                </label>
                {type === 'select' && fieldOpts ? (
                  <select
                    required={required}
                    value={form[key] ?? ''}
                    onChange={e => set(key, e.target.value)}
                    className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 bg-white"
                  >
                    <option value="">Select…</option>
                    {fieldOpts.map(v => <option key={v} value={v}>{v}</option>)}
                  </select>
                ) : (
                  <input
                    required={required}
                    placeholder={placeholder ?? ''}
                    value={form[key] ?? ''}
                    onChange={e => set(key, e.target.value)}
                    className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
                  />
                )}
              </div>
            );
          })}
        </div>

        <div className="mt-6 flex justify-end gap-3">
          <button type="button" onClick={() => navigate(-1)} className="px-4 py-2 text-sm border border-slate-200 rounded-lg hover:bg-slate-100">
            Cancel
          </button>
          <button type="submit" disabled={saving} className="px-6 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50">
            {saving ? 'Saving…' : 'Add Video'}
          </button>
        </div>
      </form>
    </div>
  );
}
