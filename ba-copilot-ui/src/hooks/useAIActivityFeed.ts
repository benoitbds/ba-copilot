import { useState, useEffect, useRef, useCallback } from 'react';

export type AIEventType = 
  | 'prompt' 
  | 'response' 
  | 'thinking' 
  | 'error' 
  | 'info' 
  | 'start' 
  | 'complete' 
  | 'warning';

export interface AIEvent {
  id: number;
  session_id: number;
  agent_name: string;
  event_type: AIEventType;
  content: string;
  event_data?: Record<string, any>;  // Renommé de metadata
  created_at: string;
}

export interface AIActivitySession {
  id: number;
  title: string;
  action_type: string;
  status: 'pending' | 'in_progress' | 'completed';
  project_id?: number;
  session_data?: Record<string, any>;  // Renommé de metadata
  created_at: string;
  completed_at?: string;
  events: AIEvent[];
}

interface UseAIActivityFeedProps {
  sessionId?: number;
  projectId?: number;
  baseUrl?: string;
  onError?: (error: string) => void;
}

export interface AIEventTypeMeta {
  label: string;
  color: string;
  icon: string;
}

export const AI_EVENT_TYPES: Record<AIEventType, AIEventTypeMeta> = {
  prompt: {
    label: 'Prompt',
    color: 'var(--color-secondary)',
    icon: '💬'
  },
  response: {
    label: 'Réponse',
    color: 'var(--color-primary)',
    icon: '🤖'
  },
  thinking: {
    label: 'Réflexion',
    color: 'var(--color-accent)',
    icon: '🧠'
  },
  error: {
    label: 'Erreur',
    color: 'var(--color-error)',
    icon: '❌'
  },
  info: {
    label: 'Info',
    color: 'var(--color-text-secondary)',
    icon: 'ℹ️'
  },
  start: {
    label: 'Début',
    color: 'var(--color-success)',
    icon: '🚀'
  },
  complete: {
    label: 'Terminé',
    color: 'var(--color-success)',
    icon: '✅'
  },
  warning: {
    label: 'Attention',
    color: 'var(--color-warning)',
    icon: '⚠️'
  }
};

export const useAIActivityFeed = ({
  sessionId,
  projectId,
  baseUrl = import.meta.env.VITE_API_URL || 'http://192.168.1.93:8000',
  onError
}: UseAIActivityFeedProps = {}) => {
  const [events, setEvents] = useState<AIEvent[]>([]);
  const [session, setSession] = useState<AIActivitySession | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isActive, setIsActive] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  // Construire l'URL WebSocket
  const getWebSocketUrl = useCallback(() => {
    const wsBaseUrl = baseUrl.replace(/^http/, 'ws');
    
    if (sessionId) {
      return `${wsBaseUrl}/ws/ai-activity/${sessionId}`;
    } else if (projectId) {
      return `${wsBaseUrl}/ws/ai-activity/project/${projectId}`;
    } else {
      return `${wsBaseUrl}/ws/ai-activity`;
    }
  }, [baseUrl, sessionId, projectId]);

  // Fetch initial session data if sessionId is provided
  const fetchSessionRef = useRef<(() => Promise<void>) | null>(null);

  useEffect(() => {
    // Utilisation d'un drapeau pour éviter les appels multiples ou annulés
    let isMounted = true;
    const fetchingRef = { current: false };

    // Utiliser une fonction memoizée stable qui ne change pas à chaque render
    fetchSessionRef.current = async () => {
      // Vérifier si on est en train de fetcher déjà ou si pas de sessionId
      if (!sessionId || fetchingRef.current || !isMounted) return;
      
      fetchingRef.current = true;
      if (isMounted) {
        setIsLoading(true);
        setError(null);
      }
      
      try {
        const response = await fetch(`${baseUrl}/ai-activity/sessions/${sessionId}`);
        if (!isMounted) return; // Ne pas mettre à jour l'état si le composant est démonté
        
        if (response.ok) {
          const data = await response.json();
          if (isMounted) {
            // Mise à jour synchrone sans setTimeout pour éviter les problèmes de timing
            setSession(data);
		if (!areEventsEqual(data.events, events)) {
            setEvents(prev => mergeEvents(prev, data.events || []));
		}
          }
        } else {
          const errorMsg = `Error fetching session: ${response.statusText}`;
          if (isMounted) setError(errorMsg);
          if (onError) onError(errorMsg);
        }
      } catch (err) {
        if (!isMounted) return;
        const errorMsg = `Error fetching session: ${err}`;
        if (isMounted) setError(errorMsg);
        if (onError) onError(errorMsg);
      } finally {
        if (isMounted) setIsLoading(false);
        // Utiliser un délai court pour réinitialiser le drapeau
        setTimeout(() => {
          if (isMounted) fetchingRef.current = false;
        }, 50);
      }
    };
    
    // Exécuter la fonction fetch seulement si un sessionId est fourni
    if (sessionId && fetchSessionRef.current) {
      fetchSessionRef.current();
    }
    
    // Nettoyage - important pour éviter les mises à jour d'état après démontage
    return () => {
      isMounted = false;
    };
  }, [baseUrl, sessionId]);

  // Connect to WebSocket
  useEffect(() => {
    // Utilisation d'un drapeau pour gérer les démontages
    let isMounted = true;
    let reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
    const MAX_RECONNECT_DELAY = 5000;
    let reconnectAttempts = 0;
    
    const connectWebSocket = () => {
      if (!isMounted || !isActive) return;
      
      // Nettoyer tout timeout existant
      if (reconnectTimeout) {
        clearTimeout(reconnectTimeout);
        reconnectTimeout = null;
      }
      
      // Fermer toute connexion existante avant d'en créer une nouvelle
      if (wsRef.current) {
        console.log('Closing existing WebSocket before creating a new one');
        try {
          if (wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.close();
          }
        } catch (e) {
          console.error('Error closing WebSocket:', e);
        }
        wsRef.current = null;
      }
      
      // Vérification de sécurité : ne pas créer de WebSocket si démonté ou inactif
      if (!isMounted || !isActive) return;
      
      console.log('Creating new WebSocket connection');
      try {
        const ws = new WebSocket(getWebSocketUrl());
        
        ws.onopen = () => {
          if (!isMounted) return;
          console.log('WebSocket connected');
          setIsConnected(true);
          setError(null);
          reconnectAttempts = 0; // Réinitialiser les tentatives après une connexion réussie
        };
        
        ws.onmessage = (event) => {
          if (!isMounted) return;
          try {
            const data = JSON.parse(event.data);
            
            // Utiliser un handler séparé pour éviter les mises à jour fréquentes
            if (data.type === 'event') {
              // Batching des mises à jour d'événements pour éviter les rendus excessifs
              setEvents(prev => {
  const merged = mergeEvents(prev, [data.data]);
  if (areEventsEqual(prev, merged)) return prev;
  return merged;
});
            } else if (data.type === 'session_completed') {
              setSession(prev => {
                if (!prev) return null;
                // Ne mettre à jour que si c'est différent pour éviter des re-rendus inutiles
                if (prev.status === 'completed' && prev.completed_at === data.data.completed_at) {
                  return prev;
                }
                return {
                  ...prev, 
                  status: 'completed', 
                  completed_at: data.data.completed_at
                };
              });
            }
          } catch (err) {
            console.error('Error parsing WebSocket message:', err);
          }
        };
        
        ws.onerror = (event) => {
          if (!isMounted) return;
          console.error('WebSocket error:', event);
          setError('WebSocket connection error');
          setIsConnected(false);
          // Les erreurs sont suivies par onclose, pas besoin de gérer la reconnexion ici
        };
        
        ws.onclose = (event) => {
          if (!isMounted) return;
          console.log(`WebSocket disconnected (code: ${event.code})`);
          setIsConnected(false);
          wsRef.current = null;
          
          // Tenter de se reconnecter automatiquement si toujours actif
          if (isActive && isMounted) {
            // Backoff exponentiel limité pour éviter trop de tentatives rapides
            const delay = Math.min(1000 * Math.pow(1.5, reconnectAttempts), MAX_RECONNECT_DELAY);
            console.log(`Reconnecting in ${delay}ms (attempt ${reconnectAttempts + 1})`);
            
            reconnectTimeout = setTimeout(() => {
              if (isMounted && isActive) {
                reconnectAttempts++;
                connectWebSocket();
              }
            }, delay);
          }
        };
        
        wsRef.current = ws;
      } catch (error) {
        console.error('Error creating WebSocket:', error);
        if (isMounted) {
          setError('Failed to create WebSocket connection');
          setIsConnected(false);
        }
      }
    };
    
    // Établir la connexion WebSocket si actif (avec un délai court pour éviter les cycles de rendu)
    let connectTimeoutId: ReturnType<typeof setTimeout> | null = null;
    if (isActive && !wsRef.current) {
      connectTimeoutId = setTimeout(() => {
        if (isMounted && isActive && !wsRef.current) {
          connectWebSocket();
        }
      }, 50);
    }
    
    // Si inactif mais connexion ouverte, fermer la connexion
    if (!isActive && wsRef.current) {
      console.log('Closing WebSocket due to inactive state');
      try {
        if (wsRef.current.readyState === WebSocket.OPEN) {
          wsRef.current.close();
        }
      } catch (e) {
        console.error('Error closing WebSocket on deactivation:', e);
      }
      wsRef.current = null;
    }
    
    // Cleanup function
    return () => {
      isMounted = false;
      
      if (connectTimeoutId) {
        clearTimeout(connectTimeoutId);
      }
      
      if (reconnectTimeout) {
        clearTimeout(reconnectTimeout);
        reconnectTimeout = null;
      }
      
      if (wsRef.current) {
        try {
          if (wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.close();
          }
        } catch (e) {
          console.error('Error closing WebSocket on unmount:', e);
        }
        wsRef.current = null;
      }
    };
  }, [getWebSocketUrl, isActive]);

  // Start/stop the activity feed - ces fonctions doivent être simples pour éviter les effets de bord
  const start = useCallback(() => {
    // La mise à jour de l'état uniquement, sans référence à wsRef
    // Les effets de websocket sont gérés par useEffect
    if (!isActive) {
      setIsActive(true);
    }
  }, [isActive]);
  
  const stop = useCallback(() => {
    // La mise à jour de l'état uniquement, sans référence à wsRef
    // Les effets de websocket sont gérés par useEffect
    if (isActive) {
      setIsActive(false);
    }
  }, [isActive]);

  // Function to fetch sessions by project
  const fetchSessionsByProject = useCallback(async (projectId: number, limit = 10) => {
    try {
      const response = await fetch(`${baseUrl}/ai-activity/sessions?project_id=${projectId}&limit=${limit}`);
      if (response.ok) {
        return await response.json();
      } else {
        throw new Error(`Error fetching sessions: ${response.statusText}`);
      }
    } catch (err) {
      console.error('Error fetching sessions:', err);
      throw err;
    }
  }, [baseUrl]);

function areEventsEqual(a: AIEvent[], b: AIEvent[]) {
  if (a.length !== b.length) return false;
  for (let i = 0; i < a.length; i++) {
    if (a[i].id !== b[i].id) return false;
  }
  return true;
}

// Utilitaire de fusion et déduplication d’events (basé sur id)
function mergeEvents(oldEvents, newEvents) {
  const map = new Map();
  [...oldEvents, ...newEvents].forEach(e => map.set(e.id, e));
  // Trie par id ou par date pour la stabilité
  return Array.from(map.values()).sort((a, b) => a.id - b.id);
}
  // Dans le hook :
useEffect(() => {
  console.log('[useAIActivityFeed] useEffect: sessionId', sessionId, 'isActive', isActive);
  // ...
}, [getWebSocketUrl, isActive]);

useEffect(() => {
  if (events.length) {
    console.log('[useAIActivityFeed] events updated', events.map(e => e.id));
  }
}, [events]);
  return {
    events,
    session,
    isConnected,
    error,
    isActive,
    isLoading,
    start,
    stop,
    fetchSessionsByProject
  };
};