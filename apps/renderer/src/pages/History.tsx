

export default function History() {
    return (
        <div id="history" className="view-section active">
            <h3 style={{ marginBottom: '20px' }}>执行日志</h3>
            <div style={{
                background: 'var(--glass-bg)',
                padding: '15px',
                borderRadius: '8px',
                height: '600px',
                fontFamily: "'Courier New', monospace",
                overflowY: 'auto',
                fontSize: '13px',
                lineHeight: 1.6
            }}>
                <div style={{ color: '#888' }}>[2023-10-27 10:00:01] System started.</div>
                <div style={{ color: '#00d2ff' }}>[2023-10-27 10:05:22] Workflow "Daily Backup" initiated.</div>
                <div>[2023-10-27 10:05:23] Step 1: Open Chrome... OK</div>
                <div>[2023-10-27 10:05:25] Step 2: Navigate to AWS Console... OK</div>
                <div style={{ color: '#ffaa00' }}>[2023-10-27 10:05:28] Warning: Load time &gt; 2000ms</div>
                <div>[2023-10-27 10:05:30] Step 3: Click "S3 Buckets"... OK</div>
                <div style={{ color: '#00ff88' }}>[2023-10-27 10:05:35] Workflow completed successfully.</div>
            </div>
        </div>
    );
}
