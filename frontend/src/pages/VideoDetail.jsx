import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../api';

const FIELDS = [
  { key: 'video_name', label: 'Video Name', required: true },
  { key: 'video_ext', label: 'Extension' },
  { key: 'institution', label: 'Institution' },
  { key: 'procedure', label: 'Procedure' },
  { key: 'anon_status', label: 'Anon Status' },
  { key: 'video_path', label: 'Video Path', required: true, wide: true },
  { key: 'storage_system', label: 'Storage System' },
  { key: 'length', label: 'Length (frames)' },
  { key: 'fps', label: 'FPS' },
  { key: 'date_recorded', label: 'Date Recorded' },
  { key: 'irb_protocol', label: 'IRB Protocol' },
  { key: 'pgs_score', label: 'PGS Score' },
  { key: 'surgical_approach', label: 'Surgical Approach' },
  { key: 'annotation_status', label: 'Annotation Status' },
  { key: 'is_usable', label: 'Is Usable' },
  { key: 'notes', label: 'Notes', wide: true },
];

export default function VideoDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [video, setVideo] = useState(null);
  const [edits, setEdits] = useState({});
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [deleteConfirm, setDeleteConfirm] = useState(false);

  useEffect(() => {
    api.getVideo(id).then(setVideo).catch(e => setError(e.message));
  }, [id]);

  const startEdit = () => { setEdits({ ...video }); setEditing(true); };
  const cancelEdit = () => { setEditing(false); setEdits({}); setError(''); };

  const save = async () => {
    setSaving(true);
    setError('');
    try {
      await api.updateVideo(id, edits);
      const updated = await api.getVideo(id);
      setVideo(updated);
      setEditing(false);
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    try {
      await api.deleteVideo(id);
      navigate('/');
    } catch (e) {
      setError(e.message);
    }
  };

  if (!video) return <div className="text-center py-20 text-slate-400">{error || 'Loading…'}</div>;

  const val = (key) => editing ? edits[key] ?? '' : video[key];

  return (
    <div className="max-w-3xl space-y-6">
      <div className="flex items-center justify-between">
        <button onClick={() => navigate(-1)} className="text-sm text-slate-500 hover:text-slate-800 flex items-center gap-1">
          ← Back
        </button>
        <div className="flex gap-2">
          {editing ? (
            <>
              <button onClick={cancelEdit} className="px-4 py-2 text-sm border border-slate-200 rounded-lg hover:bg-slate-100">Cancel</button>
              <button onClick={save} disabled={saving} className="px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50">
                {saving ? 'Saving…' : 'Save'}
              </button>
            </>
          ) : (
            <>
              <button onClick={startEdit} className="px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700">Edit</button>
              <button onClick={() => setDeleteConfirm(true)} className="px-4 py-2 text-sm border border-red-200 text-red-600 rounded-lg hover:bg-red-50">Delete</button>
            </>
          )}
        </div>
      </div>

      {error && <p className="text-sm text-red-500 bg-red-50 px-4 py-2 rounded-lg">{error}</p>}

      {deleteConfirm && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-center justify-between">
          <p className="text-sm text-red-700">Delete <strong>{video.video_name}</strong> permanently?</p>
          <div className="flex gap-2">
            <button onClick={() => setDeleteConfirm(false)} className="px-3 py-1.5 text-sm border border-slate-200 rounded-lg bg-white">Cancel</button>
            <button onClick={handleDelete} className="px-3 py-1.5 text-sm bg-red-600 text-white rounded-lg">Delete</button>
          </div>
        </div>
      )}

      <div className="bg-white rounded-xl border border-slate-200 p-6">
        <div className="flex items-start justify-between mb-6">
          <div>
            <h1 className="text-xl font-semibold text-slate-900 font-mono">{video.video_name}</h1>
            <p className="text-sm text-slate-400 mt-0.5">{video.video_id}</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {FIELDS.map(({ key, label, wide }) => (
            <div key={key} className={wide ? 'md:col-span-2' : ''}>
              <label className="block text-xs font-medium text-slate-500 mb-1">{label}</label>
              {editing ? (
                <input
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
                  value={val(key)}
                  onChange={e => setEdits(ed => ({ ...ed, [key]: e.target.value }))}
                />
              ) : (
                <p className="text-sm text-slate-800 bg-slate-50 px-3 py-2 rounded-lg min-h-[36px] break-all">
                  {video[key] ?? <span className="text-slate-300">—</span>}
                </p>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
