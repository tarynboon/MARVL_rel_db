import { useState, useRef } from 'react';
import { api } from '../api';

const STATUS_STYLE = {
  inserted: { label: 'Added', cls: 'text-green-600' },
  skipped: { label: 'Skipped (duplicate)', cls: 'text-amber-600' },
  error: { label: 'Not added', cls: 'text-red-600' },
};

export default function UploadPage() {
  const [dragging, setDragging] = useState(false);
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [warningDismissed, setWarningDismissed] = useState(false);
  const inputRef = useRef();

  const handleFile = (f) => {
    if (!f?.name.endsWith('.csv')) { setError('Please select a .csv file'); return; }
    setFile(f);
    setResult(null);
    setError('');
  };

  const upload = async () => {
    if (!file) return;
    setUploading(true);
    setError('');
    try {
      const res = await api.uploadCsv(file);
      setResult(res);
      setFile(null);
      setWarningDismissed(false);
    } catch (e) {
      setError(e.message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="w-full max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Bulk Upload</h1>
        <p className="text-sm text-slate-500 mt-1">
          Upload any CSV with video metadata. The file will be cleaned and ingested automatically.
        </p>
      </div>

      <div
        className={`border-2 border-dashed rounded-xl p-12 text-center transition-colors cursor-pointer ${
          dragging ? 'border-indigo-400 bg-indigo-50' : 'border-slate-200 hover:border-slate-300 bg-white'
        }`}
        onClick={() => inputRef.current.click()}
        onDragOver={e => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={e => { e.preventDefault(); setDragging(false); handleFile(e.dataTransfer.files[0]); }}
      >
        <input ref={inputRef} type="file" accept=".csv" className="hidden" onChange={e => handleFile(e.target.files[0])} />
        {file ? (
          <div>
            <p className="font-medium text-slate-700">{file.name}</p>
            <p className="text-sm text-slate-400 mt-1">{(file.size / 1024).toFixed(1)} KB</p>
          </div>
        ) : (
          <div>
            <p className="text-slate-500">Drop a CSV file here or click to browse</p>
            <p className="text-xs text-slate-400 mt-2">CSV with columns: dataset, video_name, video_ext, video_path, length, fps, anon_status, procedure, NumID</p>
          </div>
        )}
      </div>

      {error && <p className="text-sm text-red-500 bg-red-50 px-4 py-2 rounded-lg">{error}</p>}

      {file && (
        <button
          onClick={upload}
          disabled={uploading}
          className="w-full py-3 bg-indigo-600 text-white rounded-xl font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors"
        >
          {uploading ? 'Processing…' : 'Upload & Ingest'}
        </button>
      )}

      {result && (() => {
        const rows = result.row_results || [];
        const issuesByRow = {};
        (result.issues || []).forEach(iss => {
          (issuesByRow[iss.row] ??= []).push(iss);
        });
        const inFileDupes = (result.issues || []).filter(i => i.field === 'video_name+institution');
        const showWarning = !warningDismissed && (result.skipped > 0 || inFileDupes.length > 0);

        return (
          <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-4">
            <h2 className="font-semibold text-slate-900">Ingestion Complete</h2>

            {showWarning && (
              <div className="relative bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 text-sm text-amber-800">
                <button
                  onClick={() => setWarningDismissed(true)}
                  className="absolute top-2 right-3 text-amber-500 hover:text-amber-700 text-lg leading-none"
                  aria-label="Dismiss"
                >
                  &times;
                </button>
                <p className="font-medium mb-1">Duplicate entries detected</p>
                <ul className="list-disc list-inside space-y-0.5">
                  {result.skipped > 0 && (
                    <li>{result.skipped} row{result.skipped === 1 ? '' : 's'} skipped — a video with that video_id already exists in the database.</li>
                  )}
                  {inFileDupes.length > 0 && (
                    <li>{inFileDupes.length} row{inFileDupes.length === 1 ? '' : 's'} in this file share the same video_name + institution as another row.</li>
                  )}
                </ul>
              </div>
            )}

            <div className="grid grid-cols-3 gap-4">
              {[
                ['Inserted', result.inserted, 'text-green-600 bg-green-50', 'New rows added'],
                ['Skipped', result.skipped, 'text-slate-600 bg-slate-50', 'Already existed (duplicate video_id)'],
                ['Errors', result.errors, 'text-red-600 bg-red-50', 'Rejected by the database'],
              ].map(([label, count, cls, caption]) => (
                <div key={label} className={`rounded-lg p-4 text-center ${cls}`}>
                  <p className="text-2xl font-bold">{count}</p>
                  <p className="text-sm font-medium mt-0.5">{label}</p>
                  <p className="text-[11px] opacity-70 mt-0.5">{caption}</p>
                </div>
              ))}
            </div>

            {rows.length > 0 && (
              <div>
                <p className="text-sm font-medium text-slate-700 mb-2">Row-by-row result</p>
                <div className="max-h-96 overflow-y-auto rounded-lg border border-slate-100">
                  <table className="w-full text-xs">
                    <thead className="bg-slate-50 sticky top-0">
                      <tr>
                        <th className="px-3 py-2 text-left text-slate-500">Row</th>
                        <th className="px-3 py-2 text-left text-slate-500">Video</th>
                        <th className="px-3 py-2 text-left text-slate-500">Status</th>
                        <th className="px-3 py-2 text-left text-slate-500">Why</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {rows.map((r, i) => {
                        const status = STATUS_STYLE[r.status] || { label: r.status, cls: 'text-slate-500' };
                        const notes = (issuesByRow[r.row] || []).map(iss => iss.issue).join('; ');
                        return (
                          <tr key={i} className={r.status === 'error' ? 'bg-red-50/50' : ''}>
                            <td className="px-3 py-2 text-slate-400">{r.row}</td>
                            <td className="px-3 py-2 font-medium text-slate-700">{r.video_name || r.video_id || '—'}</td>
                            <td className={`px-3 py-2 font-medium ${status.cls}`}>{status.label}</td>
                            <td className="px-3 py-2 text-slate-500">
                              {r.detail && <div>{r.detail}</div>}
                              {notes && <div className="text-slate-400 text-[11px] mt-0.5">{notes}</div>}
                              {!r.detail && !notes && '—'}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        );
      })()}
    </div>
  );
}
