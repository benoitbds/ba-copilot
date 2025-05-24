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

  // New state variables for conversational AI flow
  const [isAwaitingClarification, setIsAwaitingClarification] = useState<boolean>(false);
  const [clarificationQuestions, setClarificationQuestions] = useState<Array<{ question_id: string; text: string }>>([]);
  const [userAnswers, setUserAnswers] = useState<Record<string, string>>({}); // Store answers as { question_id: answer_text }
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);
  const [originalUserPrompt, setOriginalUserPrompt] = useState<string | null>(null); // To store the prompt that started a conversation
  
  const API_URL = import.meta.env.VITE_API_URL || '/api';

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
    setIsAwaitingClarification(false);
    setClarificationQuestions([]);
    setUserAnswers({});
    setCurrentConversationId(null);
    setOriginalUserPrompt(prompt); // Store the initial prompt

    // Reset AI Activity Feed session ID before new operation
    setCurrentSessionId(null); 
    setTimeout(() => setShowActivityPopup(true), 10);

    try {
      const res = await fetch(`${API_URL}/agents/generate_text_conversation`, { // New endpoint
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt, project_id: project.id }),
      });
      
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();

      if (data.status === "clarification_needed") {
        setIsAwaitingClarification(true);
        setClarificationQuestions(data.questions);
        setCurrentConversationId(data.conversation_id);
        // Optionally set currentSessionId for activity feed if clarification phase has one
        if (data.activity_session_id) setCurrentSessionId(data.activity_session_id);
        setPrompt(""); // Clear the input prompt
      } else if (data.status === "success") {
        setResult(data.result.data); // Assuming data.result.data holds the spec text
        if (data.activity_session_id) setCurrentSessionId(data.activity_session_id);
        // Elements extracted info is not expected from this simplified endpoint
        setOriginalUserPrompt(null); // Clear stored prompt
      } else if (data.status === "processing") {
        // Handle processing state if backend sends it
        setResult("AI is processing your request...");
        if (data.activity_session_id) setCurrentSessionId(data.activity_session_id);
      } else {
        // Handle unexpected response
        throw new Error("Unexpected response from AI service.");
      }
    } catch (e: any) {
      setError(e.message || 'Erreur lors de la génération.');
      setOriginalUserPrompt(null);
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
    setIsAwaitingClarification(false);
    setClarificationQuestions([]);
    setUserAnswers({});
    setCurrentConversationId(null);
    setOriginalUserPrompt(objective); // Store the initial objective

    setCurrentSessionId(null);
    setTimeout(() => setShowActivityPopup(true), 10);
    
    try {
      const res = await fetch(`${API_URL}/agents/generate_mermaid`, { // This endpoint is already conversational
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_id: project.id, objective: objective }),
      });
      
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();

      if (data.status === "clarification_needed") {
        setIsAwaitingClarification(true);
        setClarificationQuestions(data.questions);
        setCurrentConversationId(data.conversation_id);
        if (data.activity_session_id) setCurrentSessionId(data.activity_session_id);
      } else if (data.status === "success") {
        if (data.result.content_type === "mermaid" && data.result.data) {
          setMermaidCode(data.result.data);
          setRefreshElementsKey(prev => prev + 1); // If elements might have changed
        } else {
          throw new Error("Invalid diagram data received.");
        }
        if (data.activity_session_id) setCurrentSessionId(data.activity_session_id);
        setOriginalUserPrompt(null);
      } else if (data.status === "processing") {
        setResult("AI is processing your diagram request..."); // Or a specific diagram loading message
        if (data.activity_session_id) setCurrentSessionId(data.activity_session_id);
      } else {
        throw new Error("Unexpected response from AI diagram service.");
      }
    } catch (e: any) {
      setError(e.message || 'Erreur de génération du diagramme.');
      setOriginalUserPrompt(null);
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

  const handleAnswerChange = (question_id: string, answer_text: string) => {
    setUserAnswers(prev => ({ ...prev, [question_id]: answer_text }));
  };

  const handleSubmitAnswers = async () => {
    if (!currentConversationId || !originalUserPrompt) {
      setError("Erreur: Contexte de conversation perdu.");
      return;
    }

    const answersPayload = clarificationQuestions.map(q => ({
      answer_id: q.question_id,
      text: userAnswers[q.question_id] || "" // Send empty string if no answer
    }));

    setLoading(true);
    setError(null);
    // Optionally, update AI Activity Feed for this new step
    // setCurrentSessionId(null); // Or use a new session for this part
    // setTimeout(() => setShowActivityPopup(true), 10);


    try {
      const res = await fetch(`${API_URL}/agents/submit_answers`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          conversation_id: currentConversationId,
          answers: answersPayload,
          project_id: project.id,
          original_prompt: originalUserPrompt 
        }),
      });

      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();

      if (data.status === "success") {
        // Determine if it was a diagram or spec based on originalUserPrompt or a stored type
        // For now, assume if mermaidCode was being generated, it's a diagram.
        // A more robust way would be to store the 'agent_type' on the frontend too.
        if (data.result.content_type === "mermaid") {
          setMermaidCode(data.result.data);
          setRefreshElementsKey(prev => prev + 1);
        } else { // Assuming 'text' or 'specification'
          setResult(data.result.data);
        }
        if (data.activity_session_id) setCurrentSessionId(data.activity_session_id);
      } else {
        // It's possible submit_answers could also lead to more questions or processing state,
        // but for now, let's assume it resolves to success or error.
        throw new Error(data.message || "Erreur lors de la soumission des réponses.");
      }
    } catch (e: any) {
      setError(e.message || 'Erreur lors de la soumission des réponses.');
    } finally {
      setLoading(false);
      setIsAwaitingClarification(false);
      setClarificationQuestions([]);
      setCurrentConversationId(null);
      setOriginalUserPrompt(null);
      setUserAnswers({});
      setPrompt(""); // Clear the input prompt again
    }
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
              {result && !isAwaitingClarification && ( // Only show result if not awaiting clarification
                <div className="agent-message">
                  <div className="agent-icon">🤖</div>
                  <div className="message-content">
                    <pre>{(typeof result === 'object' ? JSON.stringify(result, null, 2) : result)}</pre>
                  </div>
                </div>
              )}
            </div>
            <div className="card-footer">
              {isAwaitingClarification && (
                <div className="clarification-section mt-3 p-3 border rounded">
                  <h4 className="text-info">L'IA a besoin de précisions :</h4>
                  {clarificationQuestions.map((q) => (
                    <div key={q.question_id} className="mb-2">
                      <label htmlFor={q.question_id} className="form-label d-block">{q.text}</label>
                      <input
                        type="text"
                        id={q.question_id}
                        value={userAnswers[q.question_id] || ""}
                        onChange={(e) => handleAnswerChange(q.question_id, e.target.value)}
                        className="form-control form-control-sm"
                        placeholder={`Réponse à ${q.question_id}`}
                      />
                    </div>
                  ))}
                  <button 
                    onClick={handleSubmitAnswers} 
                    disabled={loading} 
                    className="btn btn-success btn-sm mt-2"
                  >
                    {loading ? "Soumission..." : "Envoyer les réponses"}
                  </button>
                </div>
              )}
              <div className="chat-input-container mt-2">
                <textarea 
                  value={prompt}
                  onChange={e => setPrompt(e.target.value)}
                  placeholder={isAwaitingClarification ? "Veuillez répondre aux questions ci-dessus." : "Saisissez votre message..."}
                  rows={2}
                  className="chat-input"
                  disabled={isAwaitingClarification || loading}
                />
                <button 
                  onClick={handleGenerate}
                  disabled={!prompt.trim() || loading || isAwaitingClarification}
                  className="btn btn-primary send-button"
                >
                  {loading && !isAwaitingClarification ? "..." : "Envoyer"}
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