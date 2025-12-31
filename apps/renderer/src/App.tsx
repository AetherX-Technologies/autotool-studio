import { useState } from 'react'
import Sidebar from './layout/Sidebar'
import Dashboard from './pages/Dashboard'
import WorkflowEditor from './pages/WorkflowEditor'
import History from './pages/History'
import Settings from './pages/Settings'
import './styles/global.css'

function App() {
  const [activePage, setActivePage] = useState('dashboard')

  const renderContent = () => {
    switch (activePage) {
      case 'dashboard':
        return <Dashboard />
      case 'workflow':
        return <WorkflowEditor />
      case 'history':
        return <History />
      case 'settings':
        return <Settings />
      default:
        return <div>404</div>
    }
  }

  return (
    <div className="app-container">
      {/* Sidebar */}
      <Sidebar activePage={activePage} onNavigate={setActivePage} />

      {/* Header */}
      <header className="header" style={{ gridArea: 'header', background: 'rgba(0, 0, 0, 0.2)', backdropFilter: 'blur(5px)', borderBottom: 'var(--glass-border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 30px' }}>
        <h1 className="header-title" style={{ fontSize: '18px', fontWeight: 500 }}>
          {activePage === 'dashboard' && '仪表盘'}
          {activePage === 'workflow' && '工作流编辑器'}
          {activePage === 'history' && '执行历史'}
          {activePage === 'settings' && '设置'}
        </h1>
        <div className="header-actions" style={{ display: 'flex', gap: '15px' }}>
          <button className="btn btn-icon"><i className="fa-regular fa-bell"></i></button>
          <button className="btn btn-primary"><i className="fa-solid fa-play"></i> 运行任务</button>
        </div>
      </header>

      {/* Content */}
      <main className="content" style={{ gridArea: 'content', padding: '30px', overflowY: 'auto', position: 'relative' }}>
        {renderContent()}
      </main>
    </div>
  )
}

export default App
