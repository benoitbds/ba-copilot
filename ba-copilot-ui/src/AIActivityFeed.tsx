import React, { useState, useEffect, useRef } from 'react';
import * as AIActivityHook from './hooks/useAIActivityFeed';
import './AIActivityFeed.css';

interface AIActivityFeedProps {
  sessionId?: number;
  projectId?: number;
  autoStart?: boolean;
  maxHeight?: string;
  showControls?: boolean;
  title?: string;
  className?: string;
}

function AIActivityFeed({
  sessionId,
  projectId,
  autoStart = true,
  maxHeight = '400px',
  showControls = true,
  title = 'Activité IA',
  className = ''
}: AIActivityFeedProps) {
  const [detailMode, setDetailMode] = useState<boolean>(false);
  const { events, session, isConnected, error, isActive, isLoading, start, stop } = AIActivityHook.useAIActivityFeed({
    sessionId,
    projectId,
    onError: (err) => console.error('AIActivityFeed error:', err)
  });
  const feedRef = useRef<HTMLDivElement>(null);

  // Auto-start the feed if autoStart is true
  useEffect(() => {
    if (autoStart && !isActive) {
      start();
    }
    
    return () => {
      if (isActive) {
        stop();
      }
    };
  }, [autoStart, isActive, start, stop]);

  // Auto-scroll to the bottom when new events arrive
  const previousEventsLength = useRef(0);
  
  useEffect(() => {
    // Only trigger scroll if new events have arrived
    if (feedRef.current && events.length > previousEventsLength.current) {
      feedRef.current.scrollTop = feedRef.current.scrollHeight;
      // Update the event count reference
      previousEventsLength.current = events.length;
    }
  }, [events]);

  // Format timestamp
  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('fr-FR', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  // Render event content
  const renderEventContent = (event: AIActivityHook.AIEvent) => {
    if (event.event_type === 'prompt' || event.event_type === 'response') {
      if (detailMode) {
        // In detail mode, show full text
        return (
          <pre className="event-content-pre">
            {event.content}
          </pre>
        );
      } else {
        // In compact mode, truncate text
        const maxLength = event.event_type === 'prompt' ? 100 : 200;
        if (event.content.length > maxLength) {
          return (
            <div className="event-content-truncated">
              {event.content.substring(0, maxLength)}...
              <button 
                className="btn btn-link show-more-btn" 
                onClick={() => setDetailMode(true)}
              >
                Afficher plus
              </button>
            </div>
          );
        } else {
          return <div className="event-content">{event.content}</div>;
        }
      }
    } else {
      // For other event types, always show full content
      return <div className="event-content">{event.content}</div>;
    }
  };
// Dans le composant principal :
console.log('[AIActivityFeed] render', { events, isLoading, isConnected, isActive });

  return (
    <div className={`ai-activity-feed-container card ${className}`}>
      <div className="card-header">
        <h3 className="card-title">
          {session ? session.title : title} 
          {isConnected && <span className="connected-indicator" title="Connecté en temps réel">●</span>}
        </h3>
        {showControls && (
          <div className="activity-feed-controls">
            <button 
              className="btn btn-small btn-link"
              onClick={() => setDetailMode(!detailMode)}
            >
              {detailMode ? 'Mode simplifié' : 'Mode détaillé'}
            </button>
            {!isActive ? (
              <button 
                className="btn btn-small btn-primary"
                onClick={start}
                disabled={isConnected}
              >
                Démarrer
              </button>
            ) : (
              <button 
                className="btn btn-small btn-secondary"
                onClick={stop}
                disabled={!isConnected}
              >
                Arrêter
              </button>
            )}
          </div>
        )}
      </div>
      
      <div 
        ref={feedRef}
        className="ai-activity-feed" 
        style={{ maxHeight }}
      >
        {error && (
          <div className="error mb-2">{error}</div>
        )}
        
        {isLoading ? (
          <div className="text-tertiary text-center p-4">
            <div className="loading-spinner"></div>
            <div className="mt-2">Chargement des événements...</div>
          </div>
        ) : events.length === 0 ? (
          <div className="text-tertiary text-center p-4">
            {isConnected ? 'En attente d\'événements...' : 'Aucun événement disponible'}
          </div>
        ) : (
          <div className="timeline">
            {events.map((event) => (
              <EventItem 
                key={event.id}
                event={event}
                detailMode={detailMode}
                formatTime={formatTime}
                renderEventContent={renderEventContent}
              />
            ))}
          </div>
        )}
      </div>
      
      {session && session.status === 'completed' && (
        <div className="activity-feed-footer">
          <div className="feed-status">
            <span className="status-badge completed">Terminé</span>
            {session.completed_at && (
              <span className="feed-completion-time">
                {new Date(session.completed_at).toLocaleString('fr-FR')}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// Optimized child component with React.memo to avoid unnecessary re-renders
const EventItem = React.memo(({ 
  event, 
  detailMode, 
  formatTime, 
  renderEventContent 
}: { 
  event: AIActivityHook.AIEvent; 
  detailMode: boolean;
  formatTime: (timestamp: string) => string;
  renderEventContent: (event: AIActivityHook.AIEvent) => React.ReactNode;
}) => {
  const eventMeta = AIActivityHook.AI_EVENT_TYPES[event.event_type] || AIActivityHook.AI_EVENT_TYPES.info;
  
  return (
    <div className={`timeline-event event-type-${event.event_type}`}>
      <div className="timeline-icon" style={{ backgroundColor: eventMeta.color }}>
        {eventMeta.icon}
      </div>
      
      <div className="timeline-content">
        <div className="event-header">
          <div className="event-agent">{event.agent_name}</div>
          <div className="event-type" style={{ color: eventMeta.color }}>
            {eventMeta.label}
          </div>
          <div className="event-time">{formatTime(event.created_at)}</div>
        </div>
        
        {renderEventContent(event)}
        
        {detailMode && event.event_data && (
          <div className="event-metadata">
            <details>
              <summary>Métadonnées</summary>
              <pre>{JSON.stringify(event.event_data, null, 2)}</pre>
            </details>
            
            {/* Affichage spécial pour les prompts et full_prompt */}
            {event.event_type === 'prompt' && event.event_data.full_prompt && (
              <details className="mt-2">
                <summary>Prompt complet</summary>
                <div className="prompt-details">
                  {event.event_data.full_prompt.map((msg: any, i: number) => (
                    <div key={i} className={`prompt-message prompt-${msg.role}`}>
                      <div className="prompt-role">{msg.role}</div>
                      <pre className="prompt-content">{msg.content}</pre>
                    </div>
                  ))}
                </div>
              </details>
            )}
            
            {/* Affichage spécial pour les métadonnées de réponse */}
            {event.event_type === 'response' && event.event_data.response_metadata && (
              <details className="mt-2">
                <summary>Détails de la réponse</summary>
                <div className="response-details">
                  <div>Modèle: {event.event_data.response_metadata.model}</div>
                  <div>Tokens prompt: {event.event_data.response_metadata.usage?.prompt_tokens}</div>
                  <div>Tokens complétion: {event.event_data.response_metadata.usage?.completion_tokens}</div>
                  <div>Tokens total: {event.event_data.response_metadata.usage?.total_tokens}</div>
                </div>
              </details>
            )}
          </div>
        )}
      </div>
    </div>
  );
});

export default AIActivityFeed;