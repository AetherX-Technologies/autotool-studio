export interface Workflow {
    id: string;
    name: string;
    nodes: any[];
    edges: any[];
}

const MOCK_WORKFLOW: Workflow = {
    id: 'wf_001',
    name: 'Daily Backup',
    nodes: [
        { id: 'start_0', type: 'trigger', data: { label: 'Trigger: Daily' } },
        { id: 'node_1', type: 'action', data: { label: 'Backup Database' } }
    ],
    edges: [
        { source: 'start_0', target: 'node_1' }
    ]
};

export const WorkflowService = {
    load: async (id: string): Promise<Workflow> => {
        console.log(`Loading workflow ${id}...`);
        return new Promise(resolve => setTimeout(() => resolve(MOCK_WORKFLOW), 500));
    },

    save: async (workflow: Workflow): Promise<boolean> => {
        console.log('Saving workflow:', JSON.stringify(workflow, null, 2));
        return new Promise(resolve => setTimeout(() => resolve(true), 500));
    },

    validate: (workflow: Workflow): string[] => {
        const errors: string[] = [];
        if (!workflow.name) errors.push('Workflow name is required');
        if (workflow.nodes.length === 0) errors.push('Workflow must have at least one node');
        return errors;
    }
};
