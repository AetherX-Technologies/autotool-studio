/**
 * Initial Data based on demo condition
 */
import type { FlowDocumentJSON } from '@flowgram.ai/fixed-layout-editor';

export const initialData: FlowDocumentJSON = {
    nodes: [
        // Start Node
        {
            id: 'start_0',
            type: 'start',
            data: {
                title: 'Start',
                content: 'start flow',
            },
            blocks: [],
        },
        // Condition Node
        {
            id: 'condition_0',
            type: 'condition',
            data: {
                title: 'Check Status',
                content: 'check if active',
            },
            blocks: [
                {
                    id: 'branch_0',
                    type: 'block',
                    data: {
                        title: 'Yes',
                        content: 'is active',
                    },
                    blocks: [
                        {
                            id: 'custom_0',
                            type: 'custom',
                            data: {
                                title: 'Process',
                                content: 'Do something',
                            },
                        },
                    ],
                },
                {
                    id: 'branch_1',
                    type: 'block',
                    data: {
                        title: 'No',
                        content: 'not active',
                    },
                    blocks: [],
                },
            ],
        },
        // End Node
        {
            id: 'end_0',
            type: 'end',
            data: {
                title: 'End',
                content: 'end flow',
            },
        },
    ],
};
