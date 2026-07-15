import React, { useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { RootState } from '../store';
import { updateFormField, clearForm, setRecentInteractionsList, setMetadata } from '../store/interactionSlice';
import { saveInteractionManually, editInteractionManually, getRecentInteractions, getMetadata } from '../api';
import { Plus, Trash, Check, HelpCircle } from 'lucide-react';
import { SelectedSample } from '../types';

export const InteractionForm: React.FC = () => {
  const dispatch = useDispatch();
  const { formState, metadata, activeInteractionId, isLoading, hcpContext } = useSelector(
    (state: RootState) => state.interaction
  );

  const [selectedSampleId, setSelectedSampleId] = useState<string>('');
  const [selectedSampleQty, setSelectedSampleQty] = useState<number>(1);
  const [saveSuccess, setSaveSuccess] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Field change helper
  const handleChange = (field: keyof typeof formState, value: any) => {
    dispatch(updateFormField({ field, value }));
  };

  // Products toggle
  const handleProductToggle = (productId: number) => {
    const current = [...formState.products];
    const index = current.indexOf(productId);
    if (index > -1) {
      current.splice(index, 1);
    } else {
      current.push(productId);
    }
    handleChange('products', current);
  };

  // Materials toggle
  const handleMaterialToggle = (materialId: number) => {
    const current = [...formState.materials];
    const index = current.indexOf(materialId);
    if (index > -1) {
      current.splice(index, 1);
    } else {
      current.push(materialId);
    }
    handleChange('materials', current);
  };

  // Add sample to list
  const handleAddSample = () => {
    if (!selectedSampleId) return;
    const id = parseInt(selectedSampleId);
    const sampleItem = metadata.samples.find((s) => s.id === id);
    if (!sampleItem) return;

    // Check if already exists, update quantity
    const current = [...formState.samples];
    const existingIdx = current.findIndex((s) => s.id === id);

    if (existingIdx > -1) {
      const updated = { ...current[existingIdx] };
      updated.quantity += selectedSampleQty;
      current[existingIdx] = updated;
    } else {
      current.push({
        id,
        name: sampleItem.name,
        quantity: selectedSampleQty,
      });
    }

    handleChange('samples', current);
    setSelectedSampleId('');
    setSelectedSampleQty(1);
  };

  // Remove sample
  const handleRemoveSample = (idx: number) => {
    const current = [...formState.samples];
    current.splice(idx, 1);
    handleChange('samples', current);
  };

  // Handle Save Submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setSaveSuccess(false);

    if (!formState.hcp_id) {
      setErrorMessage("Please select a Healthcare Professional (HCP).");
      return;
    }
    if (!formState.date) {
      setErrorMessage("Please select a valid date.");
      return;
    }
    if (!formState.time) {
      setErrorMessage("Please select a valid time.");
      return;
    }

    try {
      // Pack parameters
      const payload = {
        hcp_id: parseInt(formState.hcp_id),
        interaction_type: formState.interaction_type,
        date: formState.date,
        time: formState.time,
        attendees: formState.attendees,
        topics_discussed: formState.topics_discussed,
        observed_sentiment: formState.observed_sentiment,
        outcomes: formState.outcomes,
        follow_up_actions: formState.follow_up_actions,
        products: formState.products,
        materials: formState.materials,
        samples: formState.samples.map((s) => ({ id: s.id, quantity: s.quantity })),
      };

      let result;
      if (activeInteractionId) {
        result = await editInteractionManually(activeInteractionId, payload);
      } else {
        result = await saveInteractionManually(payload);
      }

      if (result.status === 'success') {
        setSaveSuccess(true);
        setTimeout(() => setSaveSuccess(false), 3000);
        
        // Reload list and inventory counts
        const list = await getRecentInteractions();
        dispatch(setRecentInteractionsList(list));
        const meta = await getMetadata();
        dispatch(setMetadata(meta));
      }
    } catch (err: any) {
      const details = err.response?.data?.detail || err.message || "Failed to save.";
      setErrorMessage(String(details));
    }
  };

  // AI Suggestions list
  const suggestedFollowUps = hcpContext?.pending_follow_ups || [];

  return (
    <div className="interaction-form-container card">
      <div className="form-header">
        <h2>{activeInteractionId ? `Edit Interaction #${activeInteractionId}` : 'Interaction Details'}</h2>
        {activeInteractionId && (
          <button className="btn btn-secondary btn-sm" onClick={() => dispatch(clearForm())}>
            Create New
          </button>
        )}
      </div>

      <form onSubmit={handleSubmit} className="hcp-form">
        {errorMessage && <div className="error-banner">{errorMessage}</div>}
        {saveSuccess && (
          <div className="success-banner">
            <Check size={16} /> Saved Successfully to CRM!
          </div>
        )}

        <div className="form-row">
          <div className="form-group flex-1">
            <label htmlFor="hcp_id">HCP Name <span className="required">*</span></label>
            <select
              id="hcp_id"
              value={formState.hcp_id}
              onChange={(e) => handleChange('hcp_id', e.target.value)}
              className="form-control"
            >
              <option value="">Select or search doctor...</option>
              {metadata.hcps.map((hcp) => (
                <option key={hcp.id} value={hcp.id}>
                  {hcp.name} ({hcp.specialty})
                </option>
              ))}
            </select>
          </div>

          <div className="form-group flex-1">
            <label htmlFor="interaction_type">Interaction Type</label>
            <select
              id="interaction_type"
              value={formState.interaction_type}
              onChange={(e) => handleChange('interaction_type', e.target.value)}
              className="form-control"
            >
              <option value="Meeting">Meeting</option>
              <option value="Call">Call</option>
              <option value="Email">Email</option>
              <option value="Video">Video Conference</option>
            </select>
          </div>
        </div>

        <div className="form-row">
          <div className="form-group flex-1">
            <label htmlFor="date">Date</label>
            <input
              type="date"
              id="date"
              value={formState.date}
              onChange={(e) => handleChange('date', e.target.value)}
              className="form-control"
            />
          </div>

          <div className="form-group flex-1">
            <label htmlFor="time">Time</label>
            <input
              type="time"
              id="time"
              value={formState.time}
              onChange={(e) => handleChange('time', e.target.value)}
              className="form-control"
            />
          </div>
        </div>

        <div className="form-group">
          <label htmlFor="attendees">Attendees</label>
          <input
            type="text"
            id="attendees"
            placeholder="Names of other clinic attendees..."
            value={formState.attendees}
            onChange={(e) => handleChange('attendees', e.target.value)}
            className="form-control"
          />
        </div>

        <div className="form-group">
          <label htmlFor="topics_discussed">Topics Discussed</label>
          <textarea
            id="topics_discussed"
            rows={3}
            placeholder="Enter key scientific/clinical discussion points..."
            value={formState.topics_discussed}
            onChange={(e) => handleChange('topics_discussed', e.target.value)}
            className="form-control"
          />
        </div>

        {/* Products discussed */}
        <div className="form-group">
          <label>Products Discussed</label>
          <div className="checkbox-group">
            {metadata.products.map((p) => (
              <label key={p.id} className="checkbox-label">
                <input
                  type="checkbox"
                  checked={formState.products.includes(p.id)}
                  onChange={() => handleProductToggle(p.id)}
                />
                <span className="checkbox-custom"></span>
                <span className="checkbox-text">{p.name}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Materials shared */}
        <div className="form-group">
          <label>Materials Shared / Literature Handed Out</label>
          <div className="checkbox-group">
            {metadata.materials.map((m) => (
              <label key={m.id} className="checkbox-label">
                <input
                  type="checkbox"
                  checked={formState.materials.includes(m.id)}
                  onChange={() => handleMaterialToggle(m.id)}
                />
                <span className="checkbox-custom"></span>
                <span className="checkbox-text">{m.name} ({m.type})</span>
              </label>
            ))}
          </div>
        </div>

        {/* Samples distributed */}
        <div className="form-group">
          <label>Samples Distributed</label>
          <div className="sample-selector-row">
            <select
              value={selectedSampleId}
              onChange={(e) => setSelectedSampleId(e.target.value)}
              className="form-control flex-2"
            >
              <option value="">Select sample pack...</option>
              {metadata.samples.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} (Stock: {s.stock_quantity})
                </option>
              ))}
            </select>
            <input
              type="number"
              min="1"
              value={selectedSampleQty}
              onChange={(e) => setSelectedSampleQty(Math.max(1, parseInt(e.target.value) || 1))}
              className="form-control flex-1 text-center"
            />
            <button
              type="button"
              onClick={handleAddSample}
              className="btn btn-secondary btn-icon"
              title="Add Sample"
            >
              <Plus size={16} />
            </button>
          </div>

          {formState.samples.length > 0 ? (
            <div className="selected-samples-list">
              {formState.samples.map((sample, idx) => (
                <div key={sample.id} className="selected-sample-chip">
                  <span>
                    {sample.name} (Qty: <strong>{sample.quantity}</strong>)
                  </span>
                  <button
                    type="button"
                    onClick={() => handleRemoveSample(idx)}
                    className="delete-chip-btn"
                  >
                    <Trash size={12} />
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <span className="hint-text">No samples distributed.</span>
          )}
        </div>

        {/* Sentiment */}
        <div className="form-group">
          <label>Observed/Inferred HCP Sentiment</label>
          <div className="sentiment-radio-group">
            {[
              { label: 'Positive', emoji: '😊' },
              { label: 'Neutral', emoji: '😐' },
              { label: 'Negative', emoji: '😟' },
            ].map((s) => (
              <label key={s.label} className={`sentiment-label ${formState.observed_sentiment === s.label ? 'active' : ''}`}>
                <input
                  type="radio"
                  name="observed_sentiment"
                  value={s.label}
                  checked={formState.observed_sentiment === s.label}
                  onChange={(e) => handleChange('observed_sentiment', e.target.value)}
                  className="hidden-radio"
                />
                <span className="sentiment-emoji">{s.emoji}</span>
                <span className="sentiment-text">{s.label}</span>
              </label>
            ))}
          </div>
        </div>

        <div className="form-group">
          <label htmlFor="outcomes">Key Outcomes / Agreements</label>
          <textarea
            id="outcomes"
            rows={2}
            placeholder="Enter outcomes, commitments, or feedback..."
            value={formState.outcomes}
            onChange={(e) => handleChange('outcomes', e.target.value)}
            className="form-control"
          />
        </div>

        <div className="form-group">
          <label htmlFor="follow_up_actions">Follow-up Actions</label>
          <textarea
            id="follow_up_actions"
            rows={2}
            placeholder="Enter next tasks, scheduled call descriptions, etc..."
            value={formState.follow_up_actions}
            onChange={(e) => handleChange('follow_up_actions', e.target.value)}
            className="form-control"
          />
        </div>

        <div className="form-actions">
          <button type="submit" className="btn btn-primary w-full" disabled={isLoading}>
            {isLoading ? 'Saving...' : activeInteractionId ? 'Update Interaction in CRM' : 'Log Interaction in CRM'}
          </button>
        </div>
      </form>

      {/* Suggested Follow-ups drawer */}
      {suggestedFollowUps.length > 0 && (
        <div className="suggested-followups-section">
          <h3>AI Suggested Follow-ups</h3>
          <div className="suggestions-list">
            {suggestedFollowUps.map((task) => (
              <button
                key={task.id}
                type="button"
                className="suggestion-item-btn"
                onClick={() => {
                  handleChange('follow_up_actions', task.description);
                }}
              >
                <Plus size={14} className="suggest-icon" />
                <div className="suggest-text-wrapper">
                  <span className="suggest-action">{task.description}</span>
                  {task.due_date && <span className="suggest-date">Due: {task.due_date}</span>}
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
