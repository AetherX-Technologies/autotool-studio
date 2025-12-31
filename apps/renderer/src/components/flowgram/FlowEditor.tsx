/**
 * FlowGram Editor Component
 * Integrated from reference project
 */
import { useCallback, useMemo, useRef, useState, useEffect } from 'react';
import {
    FixedLayoutEditorProvider,
    EditorRenderer,
    usePlayground,
    useService,
    FlowOperationService,
} from '@flowgram.ai/fixed-layout-editor';
import type {
    FixedLayoutProps,
    FlowDocumentJSON,
    FlowNodeRegistry,
    FlowNodeJSON as FlowNodeJSONType,
    FlowNodeEntity
} from '@flowgram.ai/fixed-layout-editor';
// @ts-ignore
import { defaultFixedSemiMaterials } from '@flowgram.ai/fixed-semi-materials';
import '@flowgram.ai/fixed-layout-editor/index.css';
import '@douyinfe/semi-ui/dist/css/semi.min.css';
import { ConfigProvider } from '@douyinfe/semi-ui';
import './flowgram.css';
// @ts-ignore
import { createMinimapPlugin } from '@flowgram.ai/minimap-plugin';

import { initialData } from './config/initial-data';
// import { nodeRegistries } from './config/node-registries'; // Removed static registries
import { fetchNodeRegistries } from '../../services/api';
import { createDynamicRegistries } from './config/dynamic-registries';

/* --- Hooks --- */

export const useAddNode = () => {
    const playground = usePlayground();
    const flowOperationService = useService(FlowOperationService as unknown as any) as FlowOperationService;

    const handleAdd = (addProps: FlowNodeJSONType, dropNode: FlowNodeEntity) => {
        const blocks = addProps.blocks ? addProps.blocks : undefined;
        const entity = flowOperationService.addFromNode(dropNode, {
            ...addProps,
            blocks,
        });
        setTimeout(() => {
            playground.scrollToView({
                bounds: entity.bounds,
                scrollToCenter: true,
            });
        }, 10);
        return entity;
    };

    const handleAddBranch = (addProps: FlowNodeJSONType, dropNode: FlowNodeEntity) => {
        const index = dropNode.index + 1;
        const entity = flowOperationService.addBlock(dropNode.originParent!, addProps, {
            index,
        });
        return entity;
    };

    return {
        handleAdd,
        handleAddBranch,
    };
};

function useEditorProps(
    initialData: FlowDocumentJSON,
    nodeRegistries: FlowNodeRegistry[]
): FixedLayoutProps {
    return useMemo(() => ({
        background: true,
        readonly: false,
        initialData,
        nodeRegistries,
        getNodeDefaultRegistry(type: string) {
            return {
                type,
                meta: { defaultExpanded: true },
                formMeta: {
                    render: () => (
                        <div style={{ padding: 10 }}>
                            <div style={{ marginBottom: 5 }}>Title</div>
                        </div>
                    ),
                },
            };
        },
        materials: {
            components: {
                ...defaultFixedSemiMaterials,
                // Use defaults for adders to simplify integration
            },
        },
        nodeEngine: { enable: true },
        history: { enable: true, enableChangeNode: true },
        onAllLayersRendered: (ctx: any) => {
            setTimeout(() => {
                ctx.playground.config.fitView(ctx.document.root.bounds.pad(30));
            }, 10);
        },
        plugins: () => [
            createMinimapPlugin({
                disableLayer: true,
                enableDisplayAllNodes: true,
                canvasStyle: {
                    canvasWidth: 182,
                    canvasHeight: 102,
                    canvasPadding: 50,
                    canvasBackground: 'rgba(245, 245, 245, 1)',
                },
            }),
        ] as any,
    }) as unknown as FixedLayoutProps, [initialData, nodeRegistries]);
}

/* --- Component --- */

export default function FlowEditor() {
    const [registries, setRegistries] = useState<FlowNodeRegistry[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchNodeRegistries()
            .then((apiNodes) => {
                const dynamicRegistries = createDynamicRegistries(apiNodes);
                setRegistries(dynamicRegistries);
            })
            .catch((err) => {
                console.error("Failed to fetch registries:", err);
            })
            .finally(() => {
                setLoading(false);
            });
    }, []);

    const editorProps = useEditorProps(initialData, registries);
    const containerRef = useRef<HTMLDivElement | null>(null);
    const getPopupContainer = useCallback(
        () => containerRef.current ?? document.body,
        []
    );

    if (loading) {
        return (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%', color: '#999' }}>
                Loading Editor Resources...
            </div>
        );
    }

    return (
        <div ref={containerRef} className="flowgram-root" style={{ height: '100%', width: '100%', background: '#fff' }}>
            <ConfigProvider getPopupContainer={getPopupContainer}>
                <FixedLayoutEditorProvider {...editorProps}>
                    <EditorRenderer className="flow-editor-renderer" style={{ width: '100%', height: '100%' }} />
                </FixedLayoutEditorProvider>
            </ConfigProvider>
        </div>
    );
}
