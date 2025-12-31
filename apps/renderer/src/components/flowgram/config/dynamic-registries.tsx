import { nanoid } from 'nanoid';
// @ts-ignore
import type { FlowNodeRegistry } from '@flowgram.ai/fixed-layout-editor';
import type { NodeRegistryItem } from '../../../services/api';
import { NodePropertiesPanel } from '../properties/NodePropertiesPanel';

export function createDynamicRegistries(items: NodeRegistryItem[]): FlowNodeRegistry[] {
    return items.map((item) => ({
        type: item.type,
        meta: {
            // Map generic props
        },
        onAdd() {
            return {
                id: `${item.type.replace('.', '_')}_${nanoid(5)}`,
                type: item.type,
                data: JSON.parse(JSON.stringify(item.defaultData || {})), // Deep copy
            };
        },
        formMeta: {
            render: (props: any) => {
                // Ensure we pass the node and the fields definition
                return (
                    <NodePropertiesPanel
                        node={props.node}
                        fields={item.form?.fields || []}
                    />
                );
            },
        },
    }));
}
