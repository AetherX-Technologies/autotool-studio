

export default function Settings() {
    return (
        <div id="settings" className="view-section active">
            <div style={{ maxWidth: '600px' }}>
                <h3 style={{ marginBottom: '20px' }}>系统设置</h3>
                <div className="form-group">
                    <label className="form-label">默认下载路径</label>
                    <input type="text" className="form-input" defaultValue="C:\Users\Admin\Downloads" />
                </div>
                <div className="form-group">
                    <label className="form-label">紧急停止热键</label>
                    <input type="text" className="form-input" defaultValue="F12" />
                </div>
                <div className="form-group">
                    <label className="form-label" style={{ display: 'flex', justifyContent: 'space-between' }}>
                        开机自启动
                        <input type="checkbox" defaultChecked />
                    </label>
                </div>
                <div className="form-group">
                    <label className="form-label" style={{ display: 'flex', justifyContent: 'space-between' }}>
                        启用云端同步 (Phase 3)
                        <input type="checkbox" disabled />
                    </label>
                </div>
                <button className="btn btn-primary">保存设置</button>
            </div>
        </div>
    );
}
