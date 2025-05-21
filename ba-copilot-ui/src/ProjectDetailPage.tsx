import { useState, useEffect, useRef } from 'react';
import MermaidDiagram from './MermaidDiagram';
import Modal from './Modal';
import NodeEditForm from './NodeEditForm';
import ElementsList from './ElementsList';
import AIActivityFeed from './AIActivityFeed';
import type { MermaidNode } from './MermaidDiagram';
import './ProjectDetailPage.css';

type Project = {
  id: number;
  name: string;
};

type Props = {
  project: Project;
  onBack: () => void;
};

type ViewMode = 'diagram' | 'list';
type ElementType = 'epic' | 'feature' | 'story' | 'usecase' | 'requirement';

function ProjectDetailPage({ project, onBack }: Props) {
  // États principaux
  const [prompt, setPrompt] = useState('');
  const [result, setResult] = useState<any>(null);
  const [mermaidCode, setMermaidCode] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // États pour l'affichage et les interactions
  const [viewMode, setViewMode] = useState<ViewMode>('diagram');
  const [activeElementType, setActiveElementType] = useState<ElementType>('epic');
  const [selectedNode, setSelectedNode] = useState<MermaidNode | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [refreshElementsKey, setRefreshElementsKey] = useState(0);
  
  // États pour l'activité des agents
  const [currentSessionId, setCurrentSessionId] = useState<number | null>(null);
  const [showActivityPopup, setShowActivityPopup] = useState(false);
  const activityPopupRef = useRef<HTMLDivElement>(null);
  
  const API_URL = import.meta.env.VITE_API_URL || 'http://192.168.1.93:8000';

  // Charger le projet et son diagramme au chargement initial
  useEffect(() => {
    const fetchProjectData = async () => {
      try {
        // Charger la structure du projet
        const structureRes = await fetch(`${API_URL}/projects/${project.id}/structure`);
        if (structureRes.ok) {
          const structure = await structureRes.json();
          if (structure.latest_diagram) {
            setMermaidCode(structure.latest_diagram.mermaid_code);
          }
        }
        
        // Charger le dernier diagramme s'il n'y a pas été chargé avec la structure
        if (!mermaidCode) {
          const diagramRes = await fetch(`${API_URL}/projects/${project.id}/diagrams?limit=1`);
          if (diagramRes.ok) {
            const diagrams = await diagramRes.json();
            if (diagrams && diagrams.length > 0) {
              setMermaidCode(diagrams[0].mermaid_code);
            }
          }
        }
      } catch (error) {
        console.error("Erreur lors du chargement des données du projet:", error);
        setError("Impossible de charger les données du projet");
      }
    };
    
    if (project.id) {
      fetchProjectData();
    }
  }, [project.id, API_URL]);

  // Gérer les clics en dehors du popup d'activité pour le fermer
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        activityPopupRef.current && 
        !activityPopupRef.current.contains(event.target as Node) &&
        showActivityPopup
      ) {
        setShowActivityPopup(false);
      }
    };
    
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showActivityPopup]);

  /**
   * Génération de contenu avec agents IA
   */
  const handleGenerate = async () => {
    if (!prompt.trim()) return;
    
    setLoading(true);
    setError(null);
    setResult(null);
    
    // Réinitialiser l'ID de session AVANT d'ouvrir le popup pour éviter un problème d'état
    setCurrentSessionId(null);
    
    // Montrer le popup d'activité avec un léger délai pour éviter les problèmes de rendu
    setTimeout(() => {
      setShowActivityPopup(true);
    }, 10);
    
    try {
      const res = await fetch(`${API_URL}/agents/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt, project_id: project.id }),
      });
      
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setResult(data);
      
      // Si l'API renvoie un ID de session d'activité, le stocker
      if (data.activity_session_id) {
        // Mise à jour avec un léger délai pour éviter les problèmes de rendu
        setTimeout(() => {
          setCurrentSessionId(data.activity_session_id);
        }, 10);
        
        // Si des éléments ont été extraits, rafraîchir la liste des éléments
        if (data.elements_extracted && data.elements_extracted > 0) {
          setRefreshElementsKey(prev => prev + 1);
          
          // Notification des éléments extraits
          setResult({
            ...data,
            spec: `${data.spec}\n\n---\n\n**${data.elements_info}**\n\nCes éléments ont été automatiquement extraits et ajoutés au projet.`
          });
          
          // Demander s'il faut régénérer le diagramme pour inclure les nouveaux éléments
          if (confirm("Des éléments ont été extraits. Voulez-vous mettre à jour le diagramme pour les inclure?")) {
            await generateDiagram("Inclure tous les éléments du projet");
          }
        }
      }
    } catch (e: any) {
      setError(e.message || 'Erreur lors de la génération.');
    } finally {
      setLoading(false);
    }
  };

  /**
   * Génération de diagramme Mermaid
   */
  const generateDiagram = async (objective: string) => {
    setLoading(true);
    setError(null);
    
    // Réinitialiser l'ID de session AVANT d'ouvrir le popup pour éviter un problème d'état
    setCurrentSessionId(null);
    
    // Montrer le popup d'activité avec un léger délai pour éviter les problèmes de rendu
    setTimeout(() => {
      setShowActivityPopup(true);
    }, 10);
    
    try {
      const res = await fetch(`${API_URL}/agents/generate_mermaid`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          project_id: project.id,
          objective: objective 
        }),
      });
      
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      
      if (data.mermaid) {
        setMermaidCode(data.mermaid);
        setRefreshElementsKey(prev => prev + 1);
        
        if (data.activity_session_id) {
          // Mise à jour avec un léger délai pour éviter les problèmes de rendu
          setTimeout(() => {
            setCurrentSessionId(data.activity_session_id);
          }, 10);
        }
      } else {
        throw new Error("Le diagramme n'a pas pu être généré");
      }
    } catch (e: any) {
      setError(e.message || 'Erreur de génération du diagramme.');
    } finally {
      setLoading(false);
    }
  };

  /**
   * Gestion des clics sur les nœuds du diagramme
   */
  const handleNodeClick = async (node: MermaidNode) => {
    try {
      const res = await fetch(`${API_URL}/nodes/${project.id}/${node.id}`);
      if (res.ok) {
        const nodeData = await res.json();
        setSelectedNode({
          ...node,
          description: nodeData.description || node.description || '',
          status: nodeData.status || node.status || 'pending'
        });
      } else {
        setSelectedNode(node);
      }
      setIsModalOpen(true);
    } catch (error) {
      console.error("Erreur lors de la récupération des détails du nœud:", error);
      setSelectedNode(node);
      setIsModalOpen(true);
    }
  };

  /**
   * Sauvegarde des modifications d'un nœud
   */
  const handleSaveNode = async (updatedNode: MermaidNode) => {
    try {
      const res = await fetch(`${API_URL}/nodes/update`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          project_id: project.id,
          node: updatedNode
        }),
      });
      
      if (!res.ok) throw new Error(await res.text());
      
      setIsModalOpen(false);
      setSelectedNode(null);
      setRefreshElementsKey(prev => prev + 1);
      
      // Mettre à jour le diagramme après modification
      await generateDiagram("Mettre à jour après modification");
    } catch (error) {
      setError('Erreur lors de la sauvegarde du nœud.');
    }
  };
  
  /**
   * Gère le changement de type d'élément dans la vue liste
   */
  const handleElementTypeChange = (type: ElementType) => {
    setActiveElementType(type);
  };

  return (
    <div className="project-detail-page">
      {/* En-tête */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-4">
          <button onClick={onBack} className="btn btn-secondary">
            &larr; Retour
          </button>
          <h2 className="mb-0">
            Projet : {project.name} 
            <span className="text-tertiary ml-2">#{project.id}</span>
          </h2>
        </div>
        
        {/* Contrôles de vue */}
        <div className="view-controls">
          <button 
            onClick={() => setViewMode('diagram')}
            className={`btn btn-icon ${viewMode === 'diagram' ? 'btn-primary' : 'btn-secondary'}`}
            title="Afficher en diagramme"
          >
            <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
              <path d="M3,3H21V21H3V3M9,15V17H15V15H9M7,7V9H17V7H7Z"></path>
            </svg>
          </button>
          <button 
            onClick={() => setViewMode('list')}
            className={`btn btn-icon ${viewMode === 'list' ? 'btn-primary' : 'btn-secondary'}`}
            title="Afficher en liste"
          >
            <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
              <path d="M3,4H21V8H3V4M3,10H21V14H3V10M3,16H21V20H3V16Z"></path>
            </svg>
          </button>
          
          <button 
            onClick={() => generateDiagram("Mise à jour du diagramme")}
            className="btn btn-primary ml-2"
            disabled={loading}
          >
            <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor" className="mr-1">
              <path d="M17.65,6.35C16.2,4.9 14.21,4 12,4A8,8 0 0,0 4,12A8,8 0 0,0 12,20C15.73,20 18.84,17.45 19.73,14H17.65C16.83,16.33 14.61,18 12,18A6,6 0 0,1 6,12A6,6 0 0,1 12,6C13.66,6 15.14,6.69 16.22,7.78L13,11H20V4L17.65,6.35Z"></path>
            </svg>
            Actualiser
          </button>
          
          <button 
            onClick={() => setShowActivityPopup(!showActivityPopup)}
            className="btn btn-secondary ml-2"
          >
            <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor" className="mr-1">
              <path d="M20,2H4A2,2 0 0,0 2,4V22L6,18H20A2,2 0 0,0 22,16V4A2,2 0 0,0 20,2M20,16H6L4,18V4H20"></path>
            </svg>
            {showActivityPopup ? "Masquer l'activité" : "Voir l'activité"}
          </button>
        </div>
      </div>
      
      {error && <div className="error mb-3">{error}</div>}
      
      {/* Contenu principal du projet */}
      <div className="project-content-container">
        <div className="main-content">
          {/* Affichage du diagramme ou de la liste */}
          {viewMode === 'diagram' && mermaidCode ? (
            <div className="diagram-view card">
              <div className="card-header">
                <h3 className="card-title">Diagramme fonctionnel</h3>
                <p className="text-secondary mb-0">Cliquez sur un élément du diagramme pour afficher et éditer ses détails</p>
              </div>
              <div className="card-content">
                <MermaidDiagram 
                  chart={mermaidCode} 
                  onNodeClick={handleNodeClick}
                />
              </div>
            </div>
          ) : viewMode === 'list' ? (
            <div className="list-view card">
              <div className="card-header">
                <h3 className="card-title">Éléments du projet</h3>
                <div className="element-type-tabs">
                  {(['epic', 'feature', 'story', 'usecase', 'requirement'] as ElementType[]).map(type => (
                    <button 
                      key={type}
                      onClick={() => handleElementTypeChange(type)}
                      className={`tab-button ${activeElementType === type ? 'active' : ''}`}
                    >
                      {type.charAt(0).toUpperCase() + type.slice(1)}s
                    </button>
                  ))}
                </div>
              </div>
              <div className="card-content">
                <ElementsList 
                  key={`elements-${activeElementType}-${refreshElementsKey}`}
                  project={project}
                  activeType={activeElementType}
                  onEditElement={handleNodeClick}
                  onRefresh={() => setRefreshElementsKey(prev => prev + 1)}
                />
              </div>
            </div>
          ) : (
            <div className="empty-state">
              <p>Aucun diagramme disponible. Utilisez le chat pour générer du contenu.</p>
            </div>
          )}
          
          {/* Chat avec les agents IA */}
          <div className="agent-chat card mt-4">
            <div className="card-header">
              <h3 className="card-title">Discussion avec les agents</h3>
            </div>
            <div className="card-content chat-content">
              {result && (
                <div className="agent-message">
                  <div className="agent-icon">🤖</div>
                  <div className="message-content">
                    <pre>{result.spec || (typeof result === 'object' ? JSON.stringify(result, null, 2) : result)}</pre>
                  </div>
                </div>
              )}
            </div>
            <div className="card-footer">
              <div className="chat-input-container">
                <textarea 
                  value={prompt}
                  onChange={e => setPrompt(e.target.value)}
                  placeholder="Saisissez votre message (ex: Ajoute une fonctionnalité de recherche, Modifie l'Epic 1...)"
                  rows={2}
                  className="chat-input"
                />
                <button 
                  onClick={handleGenerate}
                  disabled={!prompt.trim() || loading}
                  className="btn btn-primary send-button"
                >
                  {loading ? "..." : "Envoyer"}
                </button>
              </div>
            </div>
          </div>
        </div>
        
        {/* Popup d'activité des agents */}
        {showActivityPopup && (
          <div 
            ref={activityPopupRef}
            className="activity-popup"
          >
            <div className="activity-popup-header">
              <h3>Activité des agents</h3>
              <button onClick={() => setShowActivityPopup(false)} className="close-button">
                ×
              </button>
            </div>
            <div className="activity-popup-content">
              <AIActivityFeed
                projectId={project.id}
                sessionId={currentSessionId || undefined}
                autoStart={true}
                maxHeight="400px"
                showControls={false}
                key={`activity-feed-${currentSessionId}`} // Add key to force re-render when sessionId changes
              />
            </div>
          </div>
        )}
      </div>
      
      {/* Modal d'édition de nœud */}
      {selectedNode && (
        <Modal 
          isOpen={isModalOpen} 
          onClose={() => setIsModalOpen(false)} 
          title={`Éditer ${
            selectedNode.type === 'epic' ? 'Epic' : 
            selectedNode.type === 'feature' ? 'Feature' : 
            selectedNode.type === 'story' ? 'User Story' : 
            selectedNode.type === 'usecase' ? 'Use Case' : 
            selectedNode.type === 'requirement' ? 'Requirement' : 
            'Nœud'
          }`}
        >
          <NodeEditForm 
            node={selectedNode} 
            onSave={handleSaveNode} 
            onCancel={() => setIsModalOpen(false)}
          />
        </Modal>
      )}
    </div>
  );
}

export default ProjectDetailPage;