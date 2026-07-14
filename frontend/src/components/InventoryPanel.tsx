import React from 'react';
import { useSelector } from 'react-redux';
import { RootState } from '../store';
import { Package, FileText } from 'lucide-react';

export const InventoryPanel: React.FC = () => {
  const { metadata } = useSelector((state: RootState) => state.interaction);

  return (
    <div className="inventory-panel card">
      <div className="panel-header-sub">
        <Package size={18} className="header-icon" />
        <h3>Real-time Inventory & Materials</h3>
      </div>

      <div className="inventory-flex-layout">
        <div className="inventory-section flex-1">
          <h4>Sample Stock</h4>
          <div className="inventory-grid">
            {metadata.samples.map((s) => {
              const isLow = s.stock_quantity < 10;
              return (
                <div key={s.id} className="inventory-item">
                  <span className="item-name">{s.name}</span>
                  <span className={`item-qty ${isLow ? 'low' : ''}`}>
                    {s.stock_quantity}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        <div className="materials-section flex-1">
          <h4>Brochures & Literature</h4>
          <div className="materials-grid">
            {metadata.materials.map((m) => (
              <div key={m.id} className="material-item">
                <FileText size={12} className="text-secondary" />
                <span className="material-name">{m.name}</span>
                <span className="material-type">{m.type}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
