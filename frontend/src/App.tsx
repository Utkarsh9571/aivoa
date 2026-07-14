import React, { useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { InteractionForm } from './components/InteractionForm';
import { ChatPanel } from './components/ChatPanel';
import { HCPContextPanel } from './components/HCPContextPanel';
import { InventoryPanel } from './components/InventoryPanel';
import { getMetadata, getRecentInteractions } from './api';
import { setMetadata, setRecentInteractionsList, setError } from './store/interactionSlice';
import { RootState } from './store';
import { Heart } from 'lucide-react';

function App() {
  const dispatch = useDispatch();
  const { error } = useSelector((state: RootState) => state.interaction);

  useEffect(() => {
    const fetchInitData = async () => {
      try {
        const meta = await getMetadata();
        dispatch(setMetadata(meta));
        
        const list = await getRecentInteractions();
        dispatch(setRecentInteractionsList(list));
      } catch (err: any) {
        console.error("Failed to load initial data", err);
        dispatch(setError("Could not connect to the backend server. Please verify FastAPI is running."));
      }
    };
    fetchInitData();
  }, [dispatch]);

  return (
    <div className="app-container">
      {/* Header bar */}
      <header className="app-header">
        <div className="header-logo">
          <Heart className="heart-logo" />
          <h1>AI-First HCP Interaction Log</h1>
        </div>
        <div className="header-status">
          <span className="status-indicator online"></span>
          <span>CRM Connected (PostgreSQL)</span>
        </div>
      </header>

      {error && <div className="error-banner global">{error}</div>}

      {/* Main workspace grid layout */}
      <main className="dashboard-grid">
        {/* Left Column - Form & Profile context info */}
        <div className="grid-col-left">
          <InteractionForm />
          
          <div className="grid-row-widgets">
            <HCPContextPanel />
            <InventoryPanel />
          </div>
        </div>

        {/* Right Column - Conversational Chat Panel */}
        <div className="grid-col-right">
          <ChatPanel />
        </div>
      </main>
    </div>
  );
}

export default App;
