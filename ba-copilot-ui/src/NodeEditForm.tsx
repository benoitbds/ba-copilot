import { useState } from 'react';

// Définition locale du type MermaidNode
type MermaidNode = {
  id: string;
  type: 'epic' | 'feature' | 'story' | 'usecase' | 'requirement' | 'root';
  title: string;
  description?: string;
  status?: 'pending' | 'in_progress' | 'completed';
};

interface NodeEditFormProps {
  node: MermaidNode;
  onSave: (updatedNode: MermaidNode) => void;
  onCancel: () => void;
}

/**
 * Composant pour éditer les propriétés d'un nœud du diagramme Mermaid
 * 
 * Permet de modifier le titre, la description et le statut d'un nœud.
 * Les modifications sont envoyées au composant parent via la fonction onSave.
 */
function NodeEditForm({ node, onSave, onCancel }: NodeEditFormProps) {
  const [title, setTitle] = useState(node.title);
  const [description, setDescription] = useState(node.description || '');
  const [status, setStatus] = useState<MermaidNode['status']>(node.status || 'pending');

  /**
   * Gère la soumission du formulaire
   */
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    // Créer une version mise à jour du nœud
    const updatedNode: MermaidNode = {
      ...node,
      title,
      description,
      status
    };
    
    onSave(updatedNode);
  };

  return (
    <form onSubmit={handleSubmit}>
      <div className="form-group">
        <label htmlFor="node-title" className="form-label">Titre</label>
        <input
          id="node-title"
          type="text"
          className="input"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
        />
      </div>

      <div className="form-group">
        <label htmlFor="node-description" className="form-label">Description</label>
        <textarea
          id="node-description"
          className="input textarea"
          rows={4}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Description détaillée de cet élément..."
        />
      </div>

      <div className="form-group">
        <label htmlFor="node-status" className="form-label">Statut</label>
        <select
          id="node-status"
          className="input"
          value={status}
          onChange={(e) => setStatus(e.target.value as MermaidNode['status'])}
        >
          <option value="pending">À faire</option>
          <option value="in_progress">En cours</option>
          <option value="completed">Terminé</option>
        </select>
      </div>

      <div className="flex gap-2 justify-between mt-4">
        <button 
          type="button" 
          className="btn btn-secondary" 
          onClick={onCancel}
        >
          Annuler
        </button>
        <button 
          type="submit" 
          className="btn btn-primary"
        >
          Enregistrer
        </button>
      </div>
    </form>
  );
}

export default NodeEditForm;