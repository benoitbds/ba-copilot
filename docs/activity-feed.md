# AI Activity Feed

Le module **AI Activity Feed** permet de suivre en temps réel l'activité des agents IA dans l'application BA Copilot. Cette fonctionnalité offre une transparence accrue sur le travail effectué par les agents IA et permet de mieux comprendre leur processus de raisonnement.

## Fonctionnalités principales

- **Vue en temps réel** : Visualisation des événements générés par les agents IA en temps réel via WebSockets
- **Historique des sessions** : Consultation de l'historique des sessions d'activité IA par projet
- **Filtrage par session** : Possibilité de filtrer les événements par session spécifique
- **Détails contextuels** : Affichage des métadonnées et informations détaillées sur chaque événement
- **Différents types d'événements** : Support pour différents types d'événements (prompts, réponses, informations, erreurs, etc.)

## Architecture technique

Le système d'activité IA repose sur une architecture à trois niveaux :

1. **Modèle de données** (Backend) :
   - `AIActivitySession` : Représente une session d'activité IA complète
   - `AIEvent` : Représente un événement individuel au sein d'une session

2. **API de communication** (Backend) :
   - API REST pour l'accès aux données historiques
   - WebSockets pour les mises à jour en temps réel

3. **Interface utilisateur** (Frontend) :
   - Composant React `AIActivityFeed` pour l'affichage des événements
   - Hook React `useAIActivityFeed` pour la gestion des connexions WebSocket

## Intégration dans le projet

L'activité IA est intégrée au niveau du `ProjectDetailPage` avec un nouvel onglet dédié. Chaque fois qu'un agent IA est exécuté, une nouvelle session d'activité est créée et les événements sont automatiquement enregistrés.

### Fonctionnement des sessions

1. Une session est créée au début de chaque exécution d'agent
2. Les événements sont ajoutés à la session au fur et à mesure de l'exécution
3. La session est marquée comme terminée à la fin de l'exécution de l'agent
4. Les événements sont persistés en base de données pour consultation ultérieure

## Utilisation

### Frontend

```typescript
// Utilisation du composant AIActivityFeed
<AIActivityFeed 
  projectId={123}            // Optionnel: ID du projet pour filtrer les sessions
  sessionId={456}            // Optionnel: ID de session spécifique à afficher
  autoStart={true}           // Démarrage automatique de la connexion WebSocket
  maxHeight="600px"          // Hauteur maximale du composant
  showControls={true}        // Afficher les contrôles utilisateur
  title="Activité des agents" // Titre personnalisé
/>

// Utilisation du hook useAIActivityFeed
const { 
  events,         // Liste d'événements
  session,        // Informations sur la session actuelle
  isConnected,    // État de la connexion WebSocket
  isLoading,      // État de chargement
  error,          // Message d'erreur éventuel
  start,          // Fonction pour démarrer la connexion
  stop,           // Fonction pour arrêter la connexion
} = useAIActivityFeed({
  sessionId: 123,  // Optionnel: ID de session
  projectId: 456   // Optionnel: ID de projet
});
```

### Backend

```python
# Utilisation du gestionnaire de session d'activité
with AIActivitySessionManager(
    project_id=123,
    title="Génération de spécifications",
    action_type="generate"
) as session_manager:
    # Exécution de l'agent
    result = run_agent(prompt, callbacks=[
        session_manager.log_event
    ])
    
    # Ajout manuel d'événements
    session_manager.add_event(
        agent_name="AgentPrincipal",
        event_type="thinking",
        content="Analyse des requirements...",
        metadata={"source": "design_doc.md"}
    )
```

## Types d'événements

Le système prend en charge les types d'événements suivants :

- `prompt` : Entrées utilisateur ou prompts envoyés à l'agent
- `response` : Réponses générées par l'agent
- `thinking` : Étapes intermédiaires de raisonnement
- `error` : Erreurs rencontrées pendant l'exécution
- `info` : Informations générales sur le processus
- `start` : Début d'une nouvelle étape ou action
- `complete` : Fin d'une étape ou action
- `warning` : Avertissements non bloquants

## Exemples d'utilisation avancée

### Affichage conditionnel du feed d'activité

```tsx
function MyComponent({ projectId }) {
  const [showFeed, setShowFeed] = useState(false);
  
  return (
    <div>
      <button onClick={() => setShowFeed(!showFeed)}>
        {showFeed ? "Masquer" : "Afficher"} l'activité IA
      </button>
      
      {showFeed && (
        <AIActivityFeed 
          projectId={projectId} 
          autoStart={true}
        />
      )}
    </div>
  );
}
```

### Chargement de sessions historiques

```tsx
function ActivityHistory({ projectId }) {
  const [sessions, setSessions] = useState([]);
  const [selectedSessionId, setSelectedSessionId] = useState(null);
  const { fetchSessionsByProject } = useAIActivityFeed();
  
  useEffect(() => {
    const loadSessions = async () => {
      try {
        const data = await fetchSessionsByProject(projectId, 10);
        setSessions(data);
      } catch (err) {
        console.error("Erreur de chargement des sessions:", err);
      }
    };
    
    loadSessions();
  }, [projectId, fetchSessionsByProject]);
  
  return (
    <div>
      <h3>Historique des sessions</h3>
      <ul>
        {sessions.map(session => (
          <li key={session.id}>
            <button onClick={() => setSelectedSessionId(session.id)}>
              {session.title} - {new Date(session.created_at).toLocaleString()}
            </button>
          </li>
        ))}
      </ul>
      
      {selectedSessionId && (
        <AIActivityFeed 
          sessionId={selectedSessionId} 
          autoStart={true}
        />
      )}
    </div>
  );
}
```

## Personnalisation du style

Le composant AIActivityFeed utilise des variables CSS pour la personnalisation des couleurs et du style. Ces variables peuvent être redéfinies au niveau global pour adapter l'apparence du feed à votre thème :

```css
:root {
  --color-primary: #3f51b5;
  --color-secondary: #f50057;
  --color-accent: #ff4081;
  --color-success: #4caf50;
  --color-error: #f44336;
  --color-warning: #ff9800;
  
  --color-bg: #ffffff;
  --color-bg-secondary: #f5f5f5;
  
  --color-text: #333333;
  --color-text-secondary: #757575;
  --color-text-tertiary: #9e9e9e;
  
  --color-border: #e0e0e0;
}
```

## Considérations de performance

- Le WebSocket est automatiquement fermé lorsque le composant est démonté
- Les événements sont chargés en mode pagination pour les grandes sessions
- Le composant prend en charge le défilement automatique pour suivre les nouveaux événements
- En mode détaillé, les métadonnées sont affichées dans un élément `<details>` pour réduire l'encombrement visuel

## Futures améliorations

- Support pour le téléchargement des sessions en format JSON/CSV
- Recherche textuelle dans les événements
- Visualisation des sessions avec des graphiques pour mesurer les performances
- Support pour les notifications push lorsque de nouveaux événements sont disponibles