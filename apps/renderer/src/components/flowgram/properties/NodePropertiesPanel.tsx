import React, { useCallback } from 'react';
import { Form } from '@douyinfe/semi-ui';
// @ts-ignore
import { FlowNodeEntity } from '@flowgram.ai/fixed-layout-editor';
import type { NodeFormField } from '../../../services/api';

/**
 * Simple deep get utility
 */
function get(obj: any, path: string, defaultValue?: any) {
    const keys = path.split('.');
    let result = obj;
    for (const key of keys) {
        if (result == null) return defaultValue;
        result = result[key];
    }
    return result === undefined ? defaultValue : result;
}

/**
 * Simple deep set utility (returns new object)
 */
function set(obj: any, path: string, value: any) {
    if (obj == null) return obj;
    const keys = path.split('.');
    const newObj = { ...obj }; // Generic shallow copy
    let current = newObj;
    for (let i = 0; i < keys.length - 1; i++) {
        const key = keys[i];
        if (current[key] == null) {
            current[key] = {};
        } else {
            current[key] = { ...current[key] };
        }
        current = current[key];
    }
    current[keys[keys.length - 1]] = value;
    return newObj;
}

interface NodePropertiesPanelProps {
    node: FlowNodeEntity;
    fields: NodeFormField[];
}

export const NodePropertiesPanel: React.FC<NodePropertiesPanelProps> = ({ node, fields }) => {
    // Current node data (JSON) - node.data is reactive or we need to access it properly
    // In FlowGram, node.data is usually an observable or plain object depending on implementation.
    // Assuming we can read it directly. To trigger update, we might need a specific method.
    // Since we don't have full types, we'll try to use node.getData() if available or access .data property.

    // However, usually referencing the node itself in render might not trigger reactivity.
    // But let's assume standard behavior for now.

    const handleChange = useCallback((fieldPath: string, value: any) => {
        // Update node data using safe copy
        const currentData = node.data || {};

        // The path from registry includes 'data.', e.g., 'data.action.params.x'
        const internalPath = fieldPath.startsWith('data.') ? fieldPath.slice(5) : fieldPath;

        const newData = set(currentData, internalPath, value);

        if (typeof node.updateData === 'function') {
            node.updateData(newData);
        } else {
            // @ts-ignore
            node.data = newData;
        }
    }, [node]);

    return (
        <div style={{ padding: '12px' }}>
            <Form>
                {fields.map((field) => {
                    const internalPath = field.path.startsWith('data.') ? field.path.slice(5) : field.path;
                    const currentValue = get(node.data, internalPath);

                    switch (field.type) {
                        case 'select':
                            return (
                                <Form.Select
                                    key={field.path}
                                    label={field.label}
                                    optionList={field.options}
                                    value={currentValue}
                                    onChange={(val: any) => handleChange(field.path, val)}
                                    style={{ width: '100%' }}
                                />
                            );
                        case 'number':
                            return (
                                <Form.InputNumber
                                    key={field.path}
                                    label={field.label}
                                    value={currentValue}
                                    onChange={(val: any) => handleChange(field.path, val)}
                                    style={{ width: '100%' }}
                                />
                            );
                        case 'boolean':
                            return (
                                <Form.Switch
                                    key={field.path}
                                    label={field.label}
                                    checked={!!currentValue}
                                    onChange={(val: any) => handleChange(field.path, val)}
                                />
                            );
                        case 'text':
                        default:
                            return (
                                <Form.Input
                                    key={field.path}
                                    label={field.label}
                                    value={currentValue}
                                    onChange={(val: any) => handleChange(field.path, val)}
                                />
                            );
                    }
                })}
            </Form>
        </div>
    );
};
