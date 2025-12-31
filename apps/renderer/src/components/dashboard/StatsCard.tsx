

interface StatsCardProps {
    title: string;
    value: string | number;
    trend?: string;
    trendUp?: boolean; // true for up (green), false for down (red), undefined for neutral
    subtitle?: string; // e.g. "稳定"
}

export default function StatsCard({ title, value, trend, trendUp, subtitle }: StatsCardProps) {
    let trendClass = 'stat-trend';
    let icon = null;

    if (trendUp === true) {
        trendClass += ' trend-up';
        icon = <i className="fa-solid fa-arrow-trend-up"></i>;
    } else if (trendUp === false) {
        trendClass += ' trend-down'; // Assuming trend-down class exists or we use inline style
        icon = <i className="fa-solid fa-arrow-trend-down"></i>;
    }

    return (
        <div className="stat-card" style={{
            background: 'var(--glass-bg)',
            border: 'var(--glass-border)',
            borderRadius: '16px',
            padding: '20px',
            boxShadow: 'var(--glass-shadow)'
        }}>
            <div className="stat-title" style={{
                color: 'var(--text-secondary)',
                fontSize: '12px',
                marginBottom: '8px',
                textTransform: 'uppercase',
                letterSpacing: '1px'
            }}>{title}</div>
            <div className="stat-value" style={{
                fontSize: '28px',
                fontWeight: 700,
                marginBottom: '5px'
            }}>{value}</div>
            {(trend || subtitle) && (
                <div className={trendClass} style={{ fontSize: '12px', color: trendUp === true ? 'var(--success-color)' : (trendUp === false ? 'var(--danger-color)' : 'inherit') }}>
                    {icon} {trend}
                    {subtitle && <span style={{ color: 'var(--text-secondary)' }}>{subtitle}</span>}
                </div>
            )}
        </div>
    );
}
