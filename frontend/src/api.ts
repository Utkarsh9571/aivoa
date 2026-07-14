import axios from 'axios';
import { Metadata, InteractionFormData, ChatMessage, ToolCall } from './types';

const API_BASE_URL = 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const getMetadata = async (): Promise<Metadata> => {
  const response = await api.get<Metadata>('/metadata');
  return response.data;
};

export const getRecentInteractions = async (limit: number = 10): Promise<any[]> => {
  const response = await api.get<any[]>(`/interactions?limit=${limit}`);
  return response.data;
};

export const saveInteractionManually = async (data: any): Promise<any> => {
  const response = await api.post('/interactions', data);
  return response.data;
};

export const editInteractionManually = async (id: number, data: any): Promise<any> => {
  const response = await api.put(`/interactions/${id}`, data);
  return response.data;
};

export interface ChatResponse {
  response: string;
  current_interaction_id: number | null;
  form_data: any | null;
  hcp_context: any | null;
  tool_calls: ToolCall[];
}

export const chatWithCopilot = async (
  message: string,
  currentInteractionId: number | null
): Promise<ChatResponse> => {
  const response = await api.post<ChatResponse>('/chat', {
    message,
    current_interaction_id: currentInteractionId,
  });
  return response.data;
};
