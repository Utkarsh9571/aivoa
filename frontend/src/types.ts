export interface HCP {
  id: number;
  name: string;
  specialty: string;
  clinic_name: string;
  email: string;
  phone: string;
}

export interface Product {
  id: number;
  name: string;
  description: string;
  therapeutic_area: string;
}

export interface Material {
  id: number;
  name: string;
  type: string;
}

export interface Sample {
  id: number;
  name: string;
  stock_quantity: number;
}

export interface Metadata {
  hcps: HCP[];
  products: Product[];
  materials: Material[];
  samples: Sample[];
}

export interface SelectedSample {
  id: number;
  name: string;
  quantity: number;
}

export interface InteractionFormData {
  hcp_id: string; // empty string or id
  interaction_type: string;
  date: string;
  time: string;
  attendees: string;
  topics_discussed: string;
  observed_sentiment: string;
  outcomes: string;
  follow_up_actions: string;
  products: number[]; // product ids
  materials: number[]; // material ids
  samples: SelectedSample[]; // sample id + quantity
}

export interface ToolCall {
  name: string;
  args: any;
  status: 'success' | 'error';
  result?: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  toolCalls?: ToolCall[];
}

export interface HCPContext {
  hcp_id: number;
  name: string;
  specialty: string;
  clinic_name: string;
  email: string;
  phone: string;
  recent_interactions: any[];
  preferred_products: string[];
  pending_follow_ups: any[];
}
