import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { Metadata, InteractionFormData, ChatMessage, HCPContext, SelectedSample } from '../types';

interface InteractionState {
  metadata: Metadata;
  formState: InteractionFormData;
  activeInteractionId: number | null;
  hcpContext: HCPContext | null;
  chatHistory: ChatMessage[];
  recentInteractionsList: any[];
  isLoading: boolean;
  error: string | null;
}

const initialFormState: InteractionFormData = {
  hcp_id: '',
  interaction_type: 'Meeting',
  date: new Date().toISOString().split('T')[0],
  time: new Date().toTimeString().split(' ')[0].substring(0, 5),
  attendees: '',
  topics_discussed: '',
  observed_sentiment: 'Neutral',
  outcomes: '',
  follow_up_actions: '',
  products: [],
  materials: [],
  samples: [],
};

const initialState: InteractionState = {
  metadata: {
    hcps: [],
    products: [],
    materials: [],
    samples: [],
  },
  formState: initialFormState,
  activeInteractionId: null,
  hcpContext: null,
  chatHistory: [
    {
      id: 'welcome',
      role: 'assistant',
      content: "Hello! I am your AI CRM Copilot. You can describe your interaction naturally (e.g., 'Met Dr. Sharma today...') to automatically extract fields, search history, modify sentiment, or view doctor profiles.",
    },
  ],
  recentInteractionsList: [],
  isLoading: false,
  error: null,
};

const interactionSlice = createSlice({
  name: 'interaction',
  initialState,
  reducers: {
    setMetadata(state, action: PayloadAction<Metadata>) {
      state.metadata = action.payload;
    },
    updateFormField(state, action: PayloadAction<{ field: keyof InteractionFormData; value: any }>) {
      state.formState = {
        ...state.formState,
        [action.payload.field]: action.payload.value,
      };
    },
    setFormData(state, action: PayloadAction<Partial<InteractionFormData>>) {
      state.formState = {
        ...state.formState,
        ...action.payload,
      };
    },
    clearForm(state) {
      state.formState = {
        ...initialFormState,
        date: new Date().toISOString().split('T')[0],
        time: new Date().toTimeString().split(' ')[0].substring(0, 5),
      };
      state.activeInteractionId = null;
    },
    setActiveInteractionId(state, action: PayloadAction<number | null>) {
      state.activeInteractionId = action.payload;
    },
    setHCPContext(state, action: PayloadAction<HCPContext | null>) {
      state.hcpContext = action.payload;
    },
    setRecentInteractionsList(state, action: PayloadAction<any[]>) {
      state.recentInteractionsList = action.payload;
    },
    addMessage(state, action: PayloadAction<ChatMessage>) {
      state.chatHistory.push(action.payload);
    },
    setLoading(state, action: PayloadAction<boolean>) {
      state.isLoading = action.payload;
    },
    setError(state, action: PayloadAction<string | null>) {
      state.error = action.payload;
    },
  },
});

export const {
  setMetadata,
  updateFormField,
  setFormData,
  clearForm,
  setActiveInteractionId,
  setHCPContext,
  setRecentInteractionsList,
  addMessage,
  setLoading,
  setError,
} = interactionSlice.actions;

export default interactionSlice.reducer;
