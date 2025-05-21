// Type qui représente un nœud du diagramme Mermaid
export type MermaidNode = {
  id: string;
  type: 'epic' | 'feature' | 'story' | 'usecase' | 'requirement' | 'root';
  title: string;
  description?: string;
  status?: 'pending' | 'in_progress' | 'completed';
};