import React from 'react';
import { Files, Layers, Cpu, Sparkles } from 'lucide-react';

export default function StatCards({ stats }) {
  const docsCount = stats?.documents_count ?? 0;
  const chunksCount = stats?.chunks_count ?? 0;
  const dimension = stats?.vector_dimension ?? 384;
  const modelName = stats?.active_model ?? 'gemini-3.8-flash';
  const isReady = stats?.is_ready ?? false;

  return (
    <div className="stat-cards-container">
      <div className="stat-card">
        <div className="stat-icon">
          <Files size={18} />
        </div>
        <div>
          <div className="stat-label">Tài liệu</div>
          <div className="stat-value">{docsCount}</div>
        </div>
      </div>

      <div className="stat-card">
        <div className="stat-icon">
          <Layers size={18} />
        </div>
        <div>
          <div className="stat-label">Chunks</div>
          <div className="stat-value">{chunksCount}</div>
        </div>
      </div>

      <div className="stat-card">
        <div className="stat-icon">
          <Cpu size={18} />
        </div>
        <div>
          <div className="stat-label">Vector Dim</div>
          <div className="stat-value">{dimension}D</div>
        </div>
      </div>

      <div className="stat-card">
        <div className="stat-icon">
          <Sparkles size={18} />
        </div>
        <div>
          <div className="stat-label">Model Gemini</div>
          <div className="stat-value" style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.85rem' }}>
            <span
              style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                backgroundColor: isReady ? 'var(--nx-success)' : 'var(--nx-warning)',
                display: 'inline-block'
              }}
            />
            {modelName}
          </div>
        </div>
      </div>
    </div>
  );
}
