import { useState, useEffect } from 'react';
import type { MermaidNode } from './MermaidDiagram';

type ElementsListProps = {
  project: { id: number; name: string };
  activeType: string;
  onEditElement: (element: MermaidNode) => void;
  onRefresh: () => void;
};

type Element = {
  id: string;
  custom_id: string;
  type: string;
  title: string;
  description: string;
  status: 'pending' | 'in_progress' | 'completed';
  created_at: string;
  updated_at: string;
};

function ElementsList({ project, activeType, onEditElement, onRefresh }: ElementsListProps) {
  const [elements, setElements] = useState<Element[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const API_URL = 'http://192.168.1.93:8000';

  // Charger les éléments du type actif
  useEffect(() => {
    const fetchElements = async () => {
      setLoading(true);
      setError(null);
      
      try {
        const response = await fetch(`${API_URL}/projects/${project.id}/elements?element_type=${activeType}`);
        if (!response.ok) {
          throw new Error(`Erreur: ${response.statusText}`);
        }
        
        const data = await response.json();
        setElements(data);
      } catch (err: any) {
        setError(`Erreur lors du chargement des éléments: ${err.message}`);
        console.error('Erreur lors de la récupération des éléments:', err);
      } finally {
        setLoading(false);
      }
    };
    
    if (project.id && activeType) {
      fetchElements();
    }
  }, [project.id, activeType, onRefresh]);

  // Handler pour ouvrir la modale d'édition
  const handleEditClick = (element: Element) => {
    const mermaidNode: MermaidNode = {
      id: element.custom_id,
      type: element.type as MermaidNode['type'],
      title: element.title,
      description: element.description,
      status: element.status
    };
    onEditElement(mermaidNode);
  };

  // Format de date en français
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    }).format(date);
  };

  // Statut en français avec icône
  const getStatusDisplay = (status: string) => {
    switch (status) {
      case 'pending':
        return <span className="status-badge pending">À faire</span>;
      case 'in_progress':
        return <span className="status-badge in-progress">En cours</span>;
      case 'completed':
        return <span className="status-badge completed">Terminé</span>;
      default:
        return <span className="status-badge">{status}</span>;
    }
  };

  return (
    <div className="elements-list-container">
      {loading ? (
        <div className="loading">Chargement des éléments...</div>
      ) : error ? (
        <div className="error">{error}</div>
      ) : elements.length === 0 ? (
        <div className="text-tertiary">Aucun élément de type {activeType} trouvé.</div>
      ) : (
        <div className="table-container">
          <table className="elements-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Titre</th>
                <th>Statut</th>
                <th>Créé le</th>
                <th>Mis à jour le</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {elements.map((element) => (
                <tr key={element.id} className={`element-row status-${element.status}`}>
                  <td className="element-id">{element.custom_id}</td>
                  <td className="element-title">
                    <div>{element.title}</div>
                    {element.description && (
                      <div className="element-description">{element.description.substring(0, 100)}{element.description.length > 100 ? '...' : ''}</div>
                    )}
                  </td>
                  <td>{getStatusDisplay(element.status)}</td>
                  <td>{formatDate(element.created_at)}</td>
                  <td>{formatDate(element.updated_at)}</td>
                  <td>
                    <button 
                      className="btn btn-small btn-primary"
                      onClick={() => handleEditClick(element)}
                    >
                      Éditer
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default ElementsList;