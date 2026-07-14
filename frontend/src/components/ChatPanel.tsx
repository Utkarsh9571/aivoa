import React, { useState, useRef, useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { RootState } from '../store';
import { addMessage, setLoading, setFormData, setActiveInteractionId, setHCPContext, setMetadata, setRecentInteractionsList } from '../store/interactionSlice';
import { chatWithCopilot, getMetadata, getRecentInteractions } from '../api';
import { Send, Terminal, ChevronDown, ChevronUp, Bot, User, Sparkles } from 'lucide-react';
import { ChatMessage, ToolCall } from '../types';

export const ChatPanel: React.FC = () => {
  const dispatch = useDispatch();
  const { chatHistory, activeInteractionId, isLoading, metadata } = useSelector(
    (state: RootState) => state.interaction
  );

  const [input, setInput] = useState<string>('');
  const [expandedToolIdx, setExpandedToolIdx] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory]);

  // Suggestions for demo workflow
  const suggestions = [
    {
      label: "Log Meeting",
      text: "Met Dr. Rajesh Sharma today. Discussed CardioFlow 10mg efficacy. He was positive but concerned about pricing. Shared the cardiology patient guide and two samples. Follow up in a week.",
    },
    {
      label: "Change Sentiment",
      text: "Actually change the sentiment to neutral and follow up next Thursday.",
    },
    {
      label: "Check Profile",
      text: "Show me Dr. Sarah Jenkins profile and previous history.",
    },
    {
      label: "Check Stocks",
      text: "What samples and brochures do I have in stock?",
    },
  ];

  const handleSend = async (textToSend: string) => {
    if (!textToSend.trim() || isLoading) return;

    const userMsgId = 'user-' + Date.now();
    dispatch(
      addMessage({
        id: userMsgId,
        role: 'user',
        content: textToSend,
      })
    );
    setInput('');
    dispatch(setLoading(true));

    try {
      // API call to Backend
      const result = await chatWithCopilot(textToSend, activeInteractionId);

      // Add Assistant response
      const assistantMsgId = 'assistant-' + Date.now();
      dispatch(
        addMessage({
          id: assistantMsgId,
          role: 'assistant',
          content: result.response,
          toolCalls: result.tool_calls,
        })
      );

      // Synchronize form fields if form_data was returned
      if (result.form_data) {
        const formUpdates: any = {};
        
        // Map database response to form fields
        if (result.form_data.hcp_name) {
          const matchedHcp = metadata.hcps.find(
            (h) => h.name.toLowerCase() === result.form_data.hcp_name.toLowerCase()
          );
          if (matchedHcp) {
            formUpdates.hcp_id = String(matchedHcp.id);
          }
        }
        if (result.form_data.interaction_type) {
          formUpdates.interaction_type = result.form_data.interaction_type;
        }
        if (result.form_data.date) {
          formUpdates.date = result.form_data.date;
        }
        if (result.form_data.time) {
          formUpdates.time = result.form_data.time;
        }
        if (result.form_data.topics_discussed) {
          formUpdates.topics_discussed = result.form_data.topics_discussed;
        }
        if (result.form_data.observed_sentiment) {
          formUpdates.observed_sentiment = result.form_data.observed_sentiment;
        }
        if (result.form_data.outcomes) {
          formUpdates.outcomes = result.form_data.outcomes;
        }
        if (result.form_data.follow_up_actions) {
          formUpdates.follow_up_actions = result.form_data.follow_up_actions;
        }
        if (result.form_data.attendees) {
          formUpdates.attendees = result.form_data.attendees;
        }
        
        // Products
        if (result.form_data.products) {
          const productIds = result.form_data.products
            .map((pName: string) => metadata.products.find((p) => p.name.toLowerCase().includes(pName.toLowerCase()))?.id)
            .filter(Boolean) as number[];
          formUpdates.products = productIds;
        }
        
        // Materials
        if (result.form_data.materials) {
          const materialIds = result.form_data.materials
            .map((mName: string) => metadata.materials.find((m) => m.name.toLowerCase().includes(mName.toLowerCase()))?.id)
            .filter(Boolean) as number[];
          formUpdates.materials = materialIds;
        }
        
        // Samples
        if (result.form_data.samples) {
          formUpdates.samples = result.form_data.samples.map((s: any) => {
            const sampleObj = metadata.samples.find((samp) => samp.name.toLowerCase().includes(s.name.toLowerCase()));
            return {
              id: sampleObj ? sampleObj.id : 0,
              name: s.name,
              quantity: s.quantity,
            };
          }).filter((s: any) => s.id > 0);
        }

        dispatch(setFormData(formUpdates));
      }

      // Synchronize active interaction index
      if (result.current_interaction_id) {
        dispatch(setActiveInteractionId(result.current_interaction_id));
      }

      // Synchronize HCP profile context panel
      if (result.hcp_context) {
        dispatch(setHCPContext(result.hcp_context));
      }

      // Refresh list & metadata (specifically sample inventory counts)
      const list = await getRecentInteractions();
      dispatch(setRecentInteractionsList(list));
      const meta = await getMetadata();
      dispatch(setMetadata(meta));

    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || err.message || "Failed to communicate with agent.";
      dispatch(
        addMessage({
          id: 'error-' + Date.now(),
          role: 'assistant',
          content: `Sorry, I encountered an error: ${errorMsg}`,
        })
      );
    } finally {
      dispatch(setLoading(false));
    }
  };

  const toggleToolExpand = (msgId: string, idx: number) => {
    const key = `${msgId}-${idx}`;
    if (expandedToolIdx === key) {
      setExpandedToolIdx(null);
    } else {
      setExpandedToolIdx(key);
    }
  };

  return (
    <div className="chat-panel-container card">
      <div className="panel-header">
        <Bot size={20} className="header-icon" />
        <h2>AI Assistant</h2>
        <span className="copilot-badge">Copilot Mode</span>
      </div>

      {/* Messages stream */}
      <div className="chat-messages-stream">
        {chatHistory.map((msg) => (
          <div key={msg.id} className={`chat-message-bubble ${msg.role}`}>
            <div className="bubble-icon">
              {msg.role === 'user' ? <User size={14} /> : <Bot size={14} />}
            </div>
            <div className="bubble-content-wrapper">
              <div className="bubble-content">{msg.content}</div>

              {/* Renders actual execution records of database tools */}
              {msg.toolCalls && msg.toolCalls.length > 0 && (
                <div className="tool-execution-tracer">
                  <div className="tracer-title">
                    <Terminal size={12} /> Tool Tracing logs ({msg.toolCalls.length})
                  </div>
                  {msg.toolCalls.map((tool, idx) => {
                    const isExpanded = expandedToolIdx === `${msg.id}-${idx}`;
                    return (
                      <div key={idx} className={`tool-call-card ${tool.status}`}>
                        <button
                          type="button"
                          className="tool-call-header-btn"
                          onClick={() => toggleToolExpand(msg.id, idx)}
                        >
                          <span className="tool-status-dot"></span>
                          <span className="tool-name">
                            {tool.name}(...)
                          </span>
                          <span className="tool-status-badge">{tool.status}</span>
                          {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                        </button>

                        {isExpanded && (
                          <div className="tool-call-details">
                            <div className="detail-section">
                              <strong>Arguments extracted:</strong>
                              <pre className="json-box">{JSON.stringify(tool.args, null, 2)}</pre>
                            </div>
                            {tool.result && (
                              <div className="detail-section">
                                <strong>Output response:</strong>
                                <pre className="json-box">{tool.result}</pre>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="chat-message-bubble assistant loading">
            <div className="bubble-icon">
              <Bot size={14} />
            </div>
            <div className="loading-dots">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Suggested Scenario triggers */}
      <div className="suggestion-chips-container">
        {suggestions.map((s, idx) => (
          <button
            key={idx}
            type="button"
            className="suggestion-chip"
            onClick={() => handleSend(s.text)}
            disabled={isLoading}
          >
            <Sparkles size={12} className="chip-icon" />
            {s.label}
          </button>
        ))}
      </div>

      {/* Input container */}
      <div className="chat-input-container">
        <input
          type="text"
          placeholder="Describe interaction or ask a question..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend(input)}
          className="chat-input"
          disabled={isLoading}
        />
        <button
          onClick={() => handleSend(input)}
          className="btn btn-primary chat-send-btn"
          disabled={isLoading || !input.trim()}
        >
          <Send size={16} />
        </button>
      </div>
    </div>
  );
};
