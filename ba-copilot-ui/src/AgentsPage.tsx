import { useEffect, useState } from 'react';

type Agent = {
  name: string;
  prompt: string;
};

function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [editing, setEditing] = useState<{ [name: string]: string }>({});
  const [saving, setSaving] = useState<{ [name: string]: boolean }>({});
  const [error, setError] = useState<string | null>(null);
  const API_URL = 'http://192.168.1.93:8000';

  useEffect(() => {
    loadAgents();
  }, []);

  const loadAgents = () => {
    setError(null);
    fetch(`${API_URL}/agents`)
      .then(res => res.json())
      .then(setAgents)
      .catch(() => setError('Erreur de connexion à l\'API'));
  };

  const handleEdit = (name: string, value: string) => {
    setEditing(e => ({ ...e, [name]: value }));
  };

  const handleSave = async (name: string) => {
    setSaving(s => ({ ...s, [name]: true }));
    setError(null);
    
    try {
      const res = await fetch(`${API_URL}/agents/${name}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: editing[name] ?? '' }),
      });
      
      if (!res.ok) throw new Error(await res.text());
      const updated = await res.json();
      setAgents(a => a.map(agent => agent.name === name ? updated : agent));
    } catch (e: any) {
      setError(e.message || 'Erreur lors de la sauvegarde');
    } finally {
      setSaving(s => ({ ...s, [name]: false }));
    }
  };

  return (
    <div className="fade-in">
      <h1>⚙️ Agents IA</h1>
      
      {error && <div className="error">{error}</div>}
      
      {agents.length === 0 ? (
        <div className="loading">Chargement des agents...</div>
      ) : (
        <div className="mb-4">
          <p className="text-secondary mb-4">
            Configurez les agents IA qui analyseront vos besoins fonctionnels.
          </p>
          
          {agents.map(agent => (
            <div key={agent.name} className="card mb-4">
              <div className="card-header">
                <h3 className="card-title">{agent.name}</h3>
              </div>
              
              <div className="card-content">
                <div className="form-group">
                  <label className="form-label">Instructions de l'agent</label>
                  <textarea
                    value={editing[agent.name] ?? agent.prompt}
                    onChange={e => handleEdit(agent.name, e.target.value)}
                    rows={6}
                    className="input textarea w-full"
                  />
                </div>
              </div>
              
              <div className="card-footer">
                <button
                  onClick={() => handleSave(agent.name)}
                  disabled={saving[agent.name] || !editing[agent.name]}
                  className="btn btn-primary"
                >
                  {saving[agent.name] ? "Sauvegarde en cours..." : "Sauvegarder"}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default AgentsPage;