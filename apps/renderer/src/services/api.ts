export interface NodeFormField {
    name: string;
    label: string;
    type: 'text' | 'number' | 'select' | 'boolean';
    path: string;
    required?: boolean;
    options?: { label: string; value: string | number }[];
    defaultValue?: any;
}

export interface NodeRegistryItem {
    type: string;
    title: string;
    category: string;
    icon: string;
    ports: string[]; // 'in' | 'out'
    defaultData: Record<string, any>;
    form: {
        fields: NodeFormField[];
    };
    status: 'stable' | 'experimental';
}

export interface NodeMenuCategory {
    category: string;
    items: NodeRegistryItem[];
}

const API_BASE_URL = 'http://127.0.0.1:18765/api/v1';

export async function fetchNodeRegistries(): Promise<NodeRegistryItem[]> {
    try {
        const response = await fetch(`${API_BASE_URL}/flowgram/nodes`);
        if (!response.ok) {
            throw new Error(`Failed to fetch node registries: ${response.statusText}`);
        }
        const json = await response.json();
        // Handle standard response format { ok: true, data: [...] } or direct array
        if (json.ok && Array.isArray(json.data)) {
            return json.data;
        } else if (Array.isArray(json)) {
            return json;
        }
        console.error('Unexpected API response format:', json);
        return [];
    } catch (error) {
        console.error('Error fetching node registries:', error);
        return [];
    }
}
