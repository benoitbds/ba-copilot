import { useState, useEffect } from 'react';
import ProjectsPage from './ProjectsPage';
import AgentsPage from './AgentsPage';
import ProjectDetailPage from './ProjectDetailPage';
import './App.css';

type Project = {
  id: number;
  name: string;
};

function App() {
  const [page, setPage] = useState<'projects' | 'agents' | 'projectDetail'>('projects');
  const [currentProject, setCurrentProject] = useState<Project | null>(null);
  const [theme, setTheme] = useState<'light' | 'dark'>('light');

  useEffect(() => {
    // Vérifier la préférence de thème système
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    setTheme(prefersDark ? 'dark' : 'light');
    
    // Appliquer le thème au document
    document.documentElement.setAttribute('data-theme', prefersDark ? 'dark' : 'light');
  }, []);

  const toggleTheme = () => {
    const newTheme = theme === 'light' ? 'dark' : 'light';
    setTheme(newTheme);
    document.documentElement.setAttribute('data-theme', newTheme);
  };

  const openProject = (project: Project) => {
    setCurrentProject(project);
    setPage('projectDetail');
  };

  const goHome = () => setPage('projects');

  return (
    <div className="main-layout">
      <header className="app-header">
        <h1 className="app-title">
          <span>📋 BA Copilot</span>
        </h1>
        <button 
          className="theme-toggle" 
          onClick={toggleTheme}
          aria-label="Changer de thème"
        >
          {theme === 'light' ? '🌙' : '☀️'}
        </button>
      </header>
      
      <nav className="app-nav">
        <button 
          onClick={goHome} 
          className={`btn mr-2 ${page === 'projects' ? 'btn-primary' : 'btn-secondary'}`}
        >
          Projets
        </button>
        <button 
          onClick={() => setPage('agents')} 
          className={`btn ${page === 'agents' ? 'btn-primary' : 'btn-secondary'}`}
        >
          Agents IA
        </button>
      </nav>
      
      <main className="fade-in">
        {page === 'projects' && <ProjectsPage onOpenProject={openProject} />}
        {page === 'agents' && <AgentsPage />}
        {page === 'projectDetail' && currentProject && (
          <ProjectDetailPage project={currentProject} onBack={goHome} />
        )}
      </main>
    </div>
  );
}

export default App;