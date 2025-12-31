
import '../styles/global.css';

interface SidebarProps {
    activePage: string;
    onNavigate: (page: string) => void;
}

export default function Sidebar({ activePage, onNavigate }: SidebarProps) {
    return (
        <aside className="sidebar" style={{ gridArea: 'sidebar', background: 'rgba(0, 0, 0, 0.3)', backdropFilter: 'blur(10px)', borderRight: 'var(--glass-border)', padding: '20px', display: 'flex', flexDirection: 'column' }}>
            <div className="logo" style={{ fontSize: '20px', fontWeight: 700, color: 'var(--accent-color)', marginBottom: '40px', display: 'flex', alignItems: 'center', gap: '10px', textShadow: 'var(--accent-glow)' }}>
                <i className="fa-solid fa-bolt"></i>
                AutoTool
            </div>
            <ul className="nav-menu" style={{ listStyle: 'none', flexGrow: 1 }}>
                <NavItem
                    icon="fa-chart-line"
                    label="仪表盘"
                    isActive={activePage === 'dashboard'}
                    onClick={() => onNavigate('dashboard')}
                />
                <NavItem
                    icon="fa-diagram-project"
                    label="工作流编辑器"
                    isActive={activePage === 'workflow'}
                    onClick={() => onNavigate('workflow')}
                />
                <NavItem
                    icon="fa-clock-rotate-left"
                    label="执行历史"
                    isActive={activePage === 'history'}
                    onClick={() => onNavigate('history')}
                />
                <NavItem
                    icon="fa-gear"
                    label="设置"
                    isActive={activePage === 'settings'}
                    onClick={() => onNavigate('settings')}
                />
            </ul>
            <div className="user-profile">
                <div className="nav-item" style={{ marginBottom: '10px', padding: '12px 15px', borderRadius: '10px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '12px', color: 'var(--text-secondary)' }}>
                    <i className="fa-solid fa-right-from-bracket"></i> 退出
                </div>
            </div>
        </aside>
    );
}

function NavItem({ icon, label, isActive, onClick }: { icon: string, label: string, isActive: boolean, onClick: () => void }) {
    const activeStyle = isActive ? {
        background: 'var(--glass-bg)',
        color: 'var(--text-primary)',
        border: 'var(--glass-border)',
        boxShadow: '0 4px 15px rgba(0,0,0,0.2)'
    } : {};

    return (
        <li
            className={`nav-item ${isActive ? 'active' : ''}`}
            onClick={onClick}
            style={{
                marginBottom: '10px',
                padding: '12px 15px',
                borderRadius: '10px',
                cursor: 'pointer',
                transition: 'all 0.3s ease',
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                color: 'var(--text-secondary)',
                ...activeStyle
            }}
        >
            <i className={`fa-solid ${icon}`} style={{ fontSize: '18px' }}></i> {label}
        </li>
    );
}
