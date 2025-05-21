import { useState } from 'react';

type ElementsTabsProps = {
  activeType: string;
  onTypeChange: (type: string) => void;
};

// Types d'éléments disponibles avec leurs libellés
const elementTypes = [
  { id: 'epic', label: 'Epics' },
  { id: 'feature', label: 'Features' },
  { id: 'story', label: 'User Stories' },
  { id: 'usecase', label: 'Use Cases' },
  { id: 'requirement', label: 'Requirements' },
];

function ElementsTabs({ activeType, onTypeChange }: ElementsTabsProps) {
  return (
    <div className="elements-tabs">
      {elementTypes.map((type) => (
        <button
          key={type.id}
          className={`elements-tab ${activeType === type.id ? 'active' : ''}`}
          onClick={() => onTypeChange(type.id)}
        >
          {type.label}
        </button>
      ))}
    </div>
  );
}

export default ElementsTabs;