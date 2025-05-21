import { useEffect, useState } from 'react';

type Project = {
  id: number;
  name: string;
};

type Props = {
  onOpenProject: (project: Project) => void;
};

function ProjectsPage({ onOpenProject }: Props) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [newProject, setNewProject] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const API_URL = 'http://192.168.1.93:8000';

  useEffect(() => {
    setLoading(true);
    fetch(`${API_URL}/projects`)
      .then(res => res.json())
      .then(setProjects)
      .catch(() => setError('Erreur de connexion à l\'API'))
      .finally(() => setLoading(false));
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_URL}/projects`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newProject }),
      });
      if (!res.ok) throw new Error(await res.text());
      const project = await res.json();
      setProjects([...projects, project]);
      setNewProject('');
    } catch (e: any) {
      setError(e.message || 'Erreur création projet');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fade-in">
      <h1>📋 BA Copilot – Projets</h1>
      
      <form onSubmit={handleCreate} className="form-group mb-4">
        <div className="flex gap-2">
          <input
            value={newProject}
            onChange={e => setNewProject(e.target.value)}
            placeholder="Nouveau projet"
            disabled={loading}
            className="input"
          />
          <button 
            type="submit" 
            disabled={!newProject.trim() || loading}
            className="btn btn-primary"
          >
            Créer
          </button>
        </div>
      </form>
      
      {error && <div className="error">{error}</div>}
      
      {loading && <div className="loading">Chargement...</div>}
      
      {projects.length === 0 && !loading ? (
        <div className="card mb-4">
          <div className="card-content text-secondary">
            Aucun projet. Créez votre premier projet pour commencer.
          </div>
        </div>
      ) : (
        <div className="mb-4">
          <h2>Vos projets</h2>
          <ul className="list">
            {projects.map(p => (
              <li key={p.id} className="project-list-item">
                <div className="flex items-center gap-2">
                  <span className="card-title">{p.name}</span>
                  <span className="text-tertiary">#{p.id}</span>
                </div>
                <button 
                  onClick={() => onOpenProject(p)} 
                  className="btn btn-primary"
                >
                  Ouvrir
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export default ProjectsPage;