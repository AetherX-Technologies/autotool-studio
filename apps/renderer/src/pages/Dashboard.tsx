import StatsCard from '../components/dashboard/StatsCard';
import RecentRunsTable from '../components/dashboard/RecentRunsTable';

export default function Dashboard() {
    return (
        <div id="dashboard" className="view-section active">
            <div className="stats-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '20px', marginBottom: '30px' }}>
                <StatsCard
                    title="今日运行次数"
                    value="128"
                    trend="+12%"
                    trendUp={true}
                />
                <StatsCard
                    title="平均耗时"
                    value="4.2s"
                    subtitle="稳定"
                />
                <StatsCard
                    title="成功率"
                    value="98.5%"
                    trend="+0.5%"
                    trendUp={true}
                />
                <StatsCard
                    title="活跃工作流"
                    value="12"
                />
            </div>

            <RecentRunsTable />
        </div>
    );
}
