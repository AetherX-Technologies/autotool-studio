import FlowEditor from '../components/flowgram/FlowEditor';
import { WorkflowService, type Workflow } from '../services/workflow';
import { useState } from 'react';

export default function WorkflowEditor() {
    const [currentWorkflow, setCurrentWorkflow] = useState<Workflow | null>(null);

    const handleLoad = async () => {
        // In real FlowGram integration, we would load JSON into the editor via props or context
        const wf = await WorkflowService.load('wf_001');
        setCurrentWorkflow(wf);
        // Note: Connecting WorkflowService to FlowEditor requires using `initialData` prop update
        // or a ref to the editor context. For now, we load static data.
        alert(`Loaded: ${wf.name} (Integration Pending)`);
    };

    const handleSave = async () => {
        // Saving requires accessing the editor context.
        if (currentWorkflow) {
            console.log('Current workflow state:', currentWorkflow);
        }
        alert('Save triggered (Integration Pending)');
    };

    return (
        <div id="workflow" className="view-section active" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
            <div style={{ padding: '0 0 10px', display: 'flex', gap: '10px' }}>
                <button className="btn btn-primary" onClick={handleSave}><i className="fa-solid fa-save"></i> 保存</button>
                <button className="btn btn-icon" onClick={handleLoad}><i className="fa-solid fa-folder-open"></i></button>
            </div>
            <div className="workflow-editor flowgram-container" style={{ flexGrow: 1, border: '1px solid #333', borderRadius: 8, overflow: 'hidden' }}>
                <FlowEditor />
            </div>
        </div>
    );
}
