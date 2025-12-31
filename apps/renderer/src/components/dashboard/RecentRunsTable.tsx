

interface RunRecord {
    name: string;
    time: string;
    duration: string;
    status: 'Running' | 'Success' | 'Failed';
}

export default function RecentRunsTable() {
    // Mock data matching mockup
    const runs: RunRecord[] = [
        { name: '每日数据备份', time: '刚刚', duration: '12s', status: 'Running' },
        { name: 'Excel 报表生成', time: '10分钟前', duration: '45s', status: 'Success' },
        { name: '邮件自动回复', time: '1小时前', duration: '2s', status: 'Failed' },
    ];

    return (
        <>
            <h3 style={{ marginBottom: '20px' }}>
                <i className="fa-solid fa-list-check"></i> 最近任务
            </h3>
            <table className="data-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                    <tr>
                        <th style={{ textAlign: 'left', padding: '15px', color: 'var(--text-secondary)', fontWeight: 500, borderBottom: '1px solid rgba(255,255,255,0.1)' }}>任务名称</th>
                        <th style={{ textAlign: 'left', padding: '15px', color: 'var(--text-secondary)', fontWeight: 500, borderBottom: '1px solid rgba(255,255,255,0.1)' }}>执行时间</th>
                        <th style={{ textAlign: 'left', padding: '15px', color: 'var(--text-secondary)', fontWeight: 500, borderBottom: '1px solid rgba(255,255,255,0.1)' }}>耗时</th>
                        <th style={{ textAlign: 'left', padding: '15px', color: 'var(--text-secondary)', fontWeight: 500, borderBottom: '1px solid rgba(255,255,255,0.1)' }}>状态</th>
                        <th style={{ textAlign: 'left', padding: '15px', color: 'var(--text-secondary)', fontWeight: 500, borderBottom: '1px solid rgba(255,255,255,0.1)' }}>操作</th>
                    </tr>
                </thead>
                <tbody>
                    {runs.map((run, index) => (
                        <tr key={index}>
                            <td style={{ padding: '15px', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>{run.name}</td>
                            <td style={{ padding: '15px', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>{run.time}</td>
                            <td style={{ padding: '15px', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>{run.duration}</td>
                            <td style={{ padding: '15px', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                                <span className={`status-badge status-${run.status.toLowerCase()}`} style={{
                                    padding: '4px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: 600,
                                    background: run.status === 'Success' ? 'rgba(0, 255, 136, 0.2)' : (run.status === 'Running' ? 'rgba(0, 210, 255, 0.2)' : 'rgba(255, 51, 51, 0.2)'),
                                    color: run.status === 'Success' ? 'var(--success-color)' : (run.status === 'Running' ? 'var(--accent-color)' : 'var(--danger-color)')
                                }}>
                                    {run.status}
                                </span>
                            </td>
                            <td style={{ padding: '15px', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                                <button className="btn-icon">
                                    <i className={`fa-solid ${run.status === 'Running' ? 'fa-stop' : (run.status === 'Success' ? 'fa-rotate-right' : 'fa-bug')}`}></i>
                                </button>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </>
    );
}
