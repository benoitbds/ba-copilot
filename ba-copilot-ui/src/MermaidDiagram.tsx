import { useEffect, useRef, useState } from 'react';
import mermaid from 'mermaid';

// Type qui représente un nœud du diagramme Mermaid
export type MermaidNode = {
  id: string;
  type: 'epic' | 'feature' | 'story' | 'usecase' | 'requirement' | 'root';
  title: string;
  description?: string;
  status?: 'pending' | 'in_progress' | 'completed';
};

interface MermaidDiagramProps {
  chart: string;
  className?: string;
  onNodeClick?: (node: MermaidNode) => void;
}

/**
 * Composant MermaidDiagram
 * 
 * Rend un diagramme Mermaid interactif avec gestion des clics sur les nœuds.
 * Adapte automatiquement le thème en fonction du thème de l'application.
 */
function MermaidDiagram({ chart, className = '', onNodeClick }: MermaidDiagramProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [renderedSvg, setRenderedSvg] = useState<string>('');

  // Initialiser mermaid avec des options par défaut
  useEffect(() => {
    mermaid.initialize({
      startOnLoad: true,
      theme: document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'default',
      securityLevel: 'loose', // Nécessaire pour permettre les liens externes et les événements
      flowchart: { htmlLabels: true, curve: 'basis' },
    });
  }, []);

  // Rendre le diagramme Mermaid
  useEffect(() => {
    const renderMermaid = async () => {
      if (!containerRef.current || !chart) return;
      
      try {
        // Vider le contenu existant
        containerRef.current.innerHTML = '';
        
        // Générer un ID unique pour ce diagramme
        const id = `mermaid-${Math.random().toString(36).substr(2, 9)}`;
        
        // Rendre le diagramme
        const { svg } = await mermaid.render(id, chart);
        containerRef.current.innerHTML = svg;
        
        // Attendre que le DOM soit complètement mis à jour
        setTimeout(() => {
          // Ajouter des gestionnaires d'événements aux nœuds après le rendu
          if (onNodeClick && containerRef.current) {
            // Sélectionner tous les nœuds du diagramme
            const svgElement = containerRef.current.querySelector('svg');
            if (svgElement) {
              // Assurer que le SVG est cliquable
              svgElement.style.pointerEvents = 'auto';
              
              // Pour les diagrammes mindmap, nous ciblons plusieurs types de nœuds potentiels
              const nodeSelectors = [
                'g.mindmap-node', 
                'g.node', 
                'g[id^="flowchart-"]', 
                '.node',
                'g.cluster',
                'g.mindmap',
                'g.mermaid-node'
              ];
              
              const nodes = svgElement.querySelectorAll(nodeSelectors.join(', '));
              
              // Si aucun nœud n'est trouvé avec les sélecteurs standards, essayer de trouver tous les groupes SVG
              let processedNodes = nodes.length > 0 ? nodes : svgElement.querySelectorAll('g');
              
              console.log(`Recherche des nœuds: trouvé ${processedNodes.length} éléments potentiels`);
              
              // Force all elements to be clickable
              processedNodes.forEach((node) => {
                // Store original attributes for reset on mouseleave
                const shapes = node.querySelectorAll('rect, circle, ellipse, polygon, path');
                shapes.forEach(shape => {
                  // Store original stroke attributes
                  const originalStrokeWidth = shape.getAttribute('stroke-width') || '1';
                  const originalStroke = shape.getAttribute('stroke') || '#999';
                  shape.setAttribute('data-original-stroke-width', originalStrokeWidth);
                  shape.setAttribute('data-original-stroke', originalStroke);
                });
                
                // Add the node to the class to mark it as interactive
                node.classList.add('interactive-node');
                
                // Make absolutely sure this element is clickable
                node.style.cursor = 'pointer';
                node.style.pointerEvents = 'all';
                
                // Add a transparent overlay to improve clickability
                const rect = node.getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0) {
                  const clickArea = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
                  clickArea.setAttribute('width', '100%');
                  clickArea.setAttribute('height', '100%');
                  clickArea.setAttribute('fill', 'transparent');
                  clickArea.style.pointerEvents = 'all';
                  clickArea.style.cursor = 'pointer';
                  // Add click handler to the overlay
                  clickArea.onclick = (event) => handleNodeClick(event, node);
                  node.appendChild(clickArea);
                }
                
                // Mouse enter event (hover)
                node.addEventListener('mouseenter', () => {
                  node.classList.add('node-hover');
                  const shapes = node.querySelectorAll('rect, circle, ellipse, polygon, path');
                  shapes.forEach(shape => {
                    shape.setAttribute('stroke-width', '2');
                    shape.setAttribute('stroke', 'var(--color-primary)');
                  });
                });
                
                // Mouse leave event
                node.addEventListener('mouseleave', () => {
                  node.classList.remove('node-hover');
                  const shapes = node.querySelectorAll('rect, circle, ellipse, polygon, path');
                  shapes.forEach(shape => {
                    // Restore original values
                    const originalWidth = shape.getAttribute('data-original-stroke-width') || '1';
                    const originalColor = shape.getAttribute('data-original-stroke') || '#999';
                    shape.setAttribute('stroke-width', originalWidth);
                    shape.setAttribute('stroke', originalColor);
                  });
                });
                
                // Direct click listener on the node and all its children
                node.addEventListener('click', (event) => handleNodeClick(event, node));
                
                // Also add click listeners to all children for better coverage
                const children = node.querySelectorAll('*');
                children.forEach(child => {
                  child.style.pointerEvents = 'all'; // Ensure all children can receive events
                  child.addEventListener('click', (event) => handleNodeClick(event, node));
                });
              });
              
              console.log(`Ajouté des événements de clic à ${processedNodes.length} nœuds`);
            }
          }
        }, 100); // Short delay to ensure SVG is fully processed
      } catch (error) {
        console.error('Erreur lors du rendu Mermaid:', error);
        if (containerRef.current) {
          containerRef.current.innerHTML = `<div class="error">Erreur de rendu du diagramme: ${error}</div>`;
        }
      }
    };
    
    // Fonction de gestion des clics sur les nœuds
    const handleNodeClick = (event: Event, node: Element) => {
      event.preventDefault();
      event.stopPropagation();
      
      if (!onNodeClick) return;
      
      console.log('Node clicked:', node);
      
      // Extraire l'ID du nœud
      const nodeId = node.id || 'unknown';
      
      // Extraire le texte du nœud (peut être dans un élément text ou un élément enfant text)
      let nodeText = '';
      const textElement = node.querySelector('text');
      if (textElement) {
        nodeText = textElement.textContent || '';
      } else {
        // Si pas de texte direct, essayer de trouver du texte dans les enfants
        const textNodes = node.querySelectorAll('text');
        if (textNodes.length > 0) {
          nodeText = Array.from(textNodes)
            .map(textNode => textNode.textContent)
            .filter(Boolean)
            .join(' ');
        }
      }
      
      // Déterminer le type de nœud basé sur le texte ou l'id
      let nodeType: MermaidNode['type'] = 'epic'; // Par défaut
      
      // Déterminer le type en fonction du texte ou des attributs de classe
      if (node.classList.contains('mindmap-root') || nodeId === 'root') {
        nodeType = 'root';
      } else if (nodeText.toLowerCase().includes('epic')) {
        nodeType = 'epic';
      } else if (nodeText.toLowerCase().includes('feature')) {
        nodeType = 'feature';
      } else if (nodeText.toLowerCase().includes('story')) {
        nodeType = 'story';
      } else if (nodeText.toLowerCase().includes('uc') || nodeText.toLowerCase().includes('use case')) {
        nodeType = 'usecase';
      } else if (nodeText.toLowerCase().includes('req') || nodeText.toLowerCase().includes('requirement')) {
        nodeType = 'requirement';
      }
      
      // Extraire le titre des nœuds (différentes syntaxes possibles)
      const titleMatch = nodeText.match(/(?:Epic|Feature|Story|UC|Use Case|Req|Requirement)?\s*\d*\.?\d*\.?\d*:?\s*\(?(.*?)\)?$/);
      const title = titleMatch ? titleMatch[1].trim() : nodeText.trim();
      
      // Créer l'objet nœud à passer au callback
      const mermaidNode: MermaidNode = {
        id: nodeId,
        type: nodeType,
        title: title,
        description: '',
        status: 'pending'
      };
      
      console.log('Node data:', mermaidNode);
      
      // Appeler le callback avec l'objet nœud
      onNodeClick(mermaidNode);
    };

    renderMermaid();
  }, [chart, onNodeClick]);

  // Mise à jour du thème lorsque le thème de l'application change
  useEffect(() => {
    const observer = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        if (mutation.type === 'attributes' && mutation.attributeName === 'data-theme') {
          const theme = document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'default';
          mermaid.initialize({ theme });
          // Si un diagramme est déjà rendu, il faudrait le re-rendre avec le nouveau thème
          if (chart && containerRef.current) {
            mermaid.render(`mermaid-${Math.random().toString(36).substr(2, 9)}`, chart)
              .then(result => {
                containerRef.current!.innerHTML = result.svg;
              });
          }
        }
      }
    });
    
    observer.observe(document.documentElement, { attributes: true });
    return () => observer.disconnect();
  }, [chart]);
  
  return (
    <div 
      ref={containerRef} 
      className={`mermaid-container ${className}`}
      data-testid="mermaid-diagram"
    >
      {!chart && <div className="text-tertiary">Aucun diagramme à afficher</div>}
    </div>
  );
}

export default MermaidDiagram;