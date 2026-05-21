import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import SearchPage from './pages/SearchPage';
import VideoDetail from './pages/VideoDetail';
import UploadPage from './pages/UploadPage';
import AddVideoPage from './pages/AddVideoPage';

function Nav() {
  const cls = ({ isActive }) =>
    `px-4 py-2 rounded-md text-sm font-medium transition-colors ${
      isActive ? 'bg-indigo-600 text-white' : 'text-slate-600 hover:bg-slate-100'
    }`;
  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-10">
      <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
        <span className="font-semibold text-slate-900 tracking-tight">
          MARVL Video Database
        </span>
        <nav className="flex gap-1">
          <NavLink to="/" end className={cls}>Browse</NavLink>
          <NavLink to="/upload" className={cls}>Upload Bulk</NavLink>
          <NavLink to="/add" className={cls}>Add Single Entry</NavLink>
        </nav>
      </div>
    </header>
  );
}

export default function App() {
  return (
    <BrowserRouter basename={import.meta.env.BASE_URL}>
      <div className="min-h-screen bg-slate-50">
        <Nav />
        <main className="max-w-7xl mx-auto px-6 py-8">
          <Routes>
            <Route path="/" element={<SearchPage />} />
            <Route path="/videos/:id" element={<VideoDetail />} />
            <Route path="/upload" element={<UploadPage />} />
            <Route path="/add" element={<AddVideoPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
