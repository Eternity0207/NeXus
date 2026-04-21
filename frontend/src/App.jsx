import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import { ToastProvider } from './components/Toast';
import { RepoProvider } from './context/RepoContext';
import Overview from './pages/Overview';
import Graph from './pages/Graph';
import Search from './pages/Search';
import Chat from './pages/Chat';
import PRInsights from './pages/PRInsights';

export default function App() {
  return (
    <ToastProvider>
      <RepoProvider>
        <BrowserRouter>
          <div className="app-layout">
            <Sidebar />
            <main className="main-content">
              <Routes>
                <Route path="/" element={<Overview />} />
                <Route path="/graph" element={<Graph />} />
                <Route path="/search" element={<Search />} />
                <Route path="/chat" element={<Chat />} />
                <Route path="/pr" element={<PRInsights />} />
              </Routes>
            </main>
          </div>
        </BrowserRouter>
      </RepoProvider>
    </ToastProvider>
  );
}
