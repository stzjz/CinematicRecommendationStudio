import { useEffect, useMemo, useState } from 'react';
import {
  fetchAblation,
  fetchAlgorithms,
  fetchHealth,
  fetchHistory,
  fetchHotMovies,
  fetchMetrics,
  fetchRecommendations,
  fetchUsers,
} from './lib/api';
import MoviePosterCard from './components/MoviePosterCard';
import SectionTitle from './components/SectionTitle';
import StatCard from './components/StatCard';
import InsightCard from './components/InsightCard';

const LIMIT_OPTIONS = [4, 6, 8];

function formatMetric(value) {
  return typeof value === 'number' ? value.toFixed(3) : '-';
}

export default function App() {
  const [health, setHealth] = useState(null);
  const [users, setUsers] = useState([]);
  const [algorithms, setAlgorithms] = useState([]);
  const [hotMovies, setHotMovies] = useState([]);
  const [metrics, setMetrics] = useState([]);
  const [ablation, setAblation] = useState([]);
  const [recommendations, setRecommendations] = useState([]);
  const [history, setHistory] = useState([]);
  const [selectedUser, setSelectedUser] = useState('');
  const [selectedAlgorithm, setSelectedAlgorithm] = useState('');
  const [selectedLimit, setSelectedLimit] = useState(6);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let disposed = false;

    async function bootstrap() {
      setLoading(true);
      setError('');
      try {
        const [healthRes, usersRes, algoRes, hotRes, metricsRes, ablationRes] = await Promise.all([
          fetchHealth(),
          fetchUsers(),
          fetchAlgorithms(),
          fetchHotMovies(6),
          fetchMetrics(),
          fetchAblation(),
        ]);

        if (disposed) {
          return;
        }

        const nextUsers = usersRes.items || [];
        const nextAlgorithms = algoRes.items || [];

        setHealth(healthRes);
        setUsers(nextUsers);
        setAlgorithms(nextAlgorithms);
        setHotMovies(hotRes.items || []);
        setMetrics(metricsRes.items || []);
        setAblation(ablationRes.items || []);

        const fallbackUser = nextUsers[0]?.user_id ? String(nextUsers[0].user_id) : '';
        const fallbackAlgorithm = nextAlgorithms[0]?.name || '';

        setSelectedUser((current) => current || fallbackUser);
        setSelectedAlgorithm((current) => current || fallbackAlgorithm);
      } catch (err) {
        if (!disposed) {
          setError(err.message || String(err));
        }
      } finally {
        if (!disposed) {
          setLoading(false);
        }
      }
    }

    bootstrap();
    return () => {
      disposed = true;
    };
  }, []);

  useEffect(() => {
    let disposed = false;

    async function loadUserViews() {
      if (!selectedUser || !selectedAlgorithm) {
        return;
      }

      try {
        const [recommendationRes, historyRes] = await Promise.all([
          fetchRecommendations(selectedUser, selectedAlgorithm, selectedLimit),
          fetchHistory(selectedUser),
        ]);

        if (disposed) {
          return;
        }

        setRecommendations(recommendationRes.items || []);
        setHistory(historyRes.items || []);
      } catch (err) {
        if (!disposed) {
          setError(err.message || String(err));
        }
      }
    }

    loadUserViews();
    return () => {
      disposed = true;
    };
  }, [selectedUser, selectedAlgorithm, selectedLimit]);

  const selectedUserProfile = useMemo(
    () => users.find((user) => String(user.user_id) === String(selectedUser)),
    [users, selectedUser]
  );

  const selectedAlgorithmMeta = useMemo(
    () => algorithms.find((item) => item.name === selectedAlgorithm),
    [algorithms, selectedAlgorithm]
  );

  const topMetric = metrics[0];
  const bestAblation = ablation[ablation.length - 1];

  return (
    <div className="app-shell">
      <header className="hero-frame">
        <div className="hero-copy">
          <p className="hero-kicker">Cinematic Recommendation Studio</p>
          <h1>把推荐系统做成一场有质感的电影首映礼。</h1>
          <p className="hero-text">
            这个前端项目直接消费你们已经搭好的后端 API，用更完整的视觉语言把个性化推荐、热门影片、历史偏好和实验指标串成一条答辩叙事线。
          </p>
          <div className="hero-actions">
            <a href="http://127.0.0.1:8000/docs" target="_blank" rel="noreferrer">
              查看 API 文档
            </a>
            <span>数据源：{health?.data_source?.toUpperCase() || '-'}</span>
          </div>
        </div>
        <div className="hero-stage">
          <div className="spotlight-card primary">
            <span>Selected User</span>
            <strong>{selectedUserProfile?.username || 'Loading'}</strong>
            <p>{selectedUserProfile ? `${selectedUserProfile.occupation} · ${selectedUserProfile.age} 岁` : '正在读取用户画像'}</p>
          </div>
          <div className="spotlight-card secondary">
            <span>Current Algorithm</span>
            <strong>{selectedAlgorithmMeta?.name || 'Loading'}</strong>
            <p>{selectedAlgorithmMeta?.description || '等待算法信息'}</p>
          </div>
        </div>
      </header>

      <section className="control-board">
        <SectionTitle
          eyebrow="Live Controls"
          title="推荐面板"
          description="切换用户、基线算法和展示条数，前端会实时重新拉取推荐结果。"
        />
        <div className="control-grid">
          <label>
            <span>用户</span>
            <select value={selectedUser} onChange={(event) => setSelectedUser(event.target.value)}>
              {users.map((user) => (
                <option key={user.user_id} value={user.user_id}>
                  {user.user_id} - {user.username}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>算法</span>
            <select value={selectedAlgorithm} onChange={(event) => setSelectedAlgorithm(event.target.value)}>
              {algorithms.map((algorithm) => (
                <option key={algorithm.name} value={algorithm.name}>
                  {algorithm.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>展示条数</span>
            <select value={selectedLimit} onChange={(event) => setSelectedLimit(Number(event.target.value))}>
              {LIMIT_OPTIONS.map((limit) => (
                <option key={limit} value={limit}>
                  Top {limit}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="stat-grid">
          <StatCard label="Users" value={users.length || '-'} accent="gold" />
          <StatCard label="Algorithms" value={algorithms.length || '-'} accent="cyan" />
          <StatCard label="Hot Titles" value={hotMovies.length || '-'} accent="mint" />
          <StatCard label="Data Source" value={health?.data_source?.toUpperCase() || '-'} accent="rose" />
        </div>
      </section>

      {error ? <section className="error-banner">页面加载失败：{error}</section> : null}
      {loading ? <section className="loading-banner">正在加载前端展示数据...</section> : null}

      <section className="layout-grid">
        <div className="panel-block wide">
          <SectionTitle
            eyebrow="Top Picks"
            title="个性化推荐结果"
            description={selectedAlgorithmMeta?.description || '当前选中算法的推荐结果会展示在这里。'}
          />
          <div className="poster-grid">
            {recommendations.map((movie, index) => (
              <MoviePosterCard key={`${movie.movie_id}-${selectedAlgorithm}`} movie={movie} index={index} />
            ))}
            {!recommendations.length && !loading ? <div className="empty-card">当前没有可展示的推荐结果。</div> : null}
          </div>
        </div>

        <div className="panel-block side">
          <SectionTitle
            eyebrow="User Taste"
            title="历史偏好"
            description="这些影片用来解释用户为何会拿到当前推荐。"
          />
          <div className="stack-list">
            {history.slice(0, 6).map((movie) => (
              <article key={`history-${movie.movie_id}`} className="stack-card">
                <div>
                  <h3>{movie.title}</h3>
                  <p>{(movie.genres || []).join(' / ')}</p>
                </div>
                <strong>{Number(movie.rating).toFixed(1)}</strong>
              </article>
            ))}
            {!history.length && !loading ? <div className="empty-card">该用户暂无历史记录。</div> : null}
          </div>
        </div>
      </section>

      <section className="layout-grid">
        <div className="panel-block wide">
          <SectionTitle
            eyebrow="Homepage Shelf"
            title="热门电影陈列"
            description="答辩时很适合放在首页，既能撑起视觉也能兜底冷启动。"
          />
          <div className="poster-grid compact">
            {hotMovies.map((movie, index) => (
              <MoviePosterCard key={`hot-${movie.movie_id}`} movie={movie} index={index + 10} />
            ))}
          </div>
        </div>

        <div className="panel-block side">
          <SectionTitle
            eyebrow="Experiment Signals"
            title="模型指标"
            description="把后端实验结果做成更像产品面板的展示方式。"
          />
          <div className="insight-grid">
            {metrics.map((metric) => (
              <InsightCard
                key={metric.model_name}
                title={metric.model_name}
                lines={[
                  `HR@10 ${formatMetric(metric.hr10)}`,
                  `NDCG@10 ${formatMetric(metric.ndcg10)}`,
                  metric.remark || 'baseline metric',
                ]}
              />
            ))}
            {topMetric ? (
              <InsightCard
                title="Current Highlight"
                accent="feature"
                lines={[
                  `当前首个指标卡：${topMetric.model_name}`,
                  `这块区域后续可以替换成 NeuMF / LightGCN 的正式结果。`,
                ]}
              />
            ) : null}
          </div>
        </div>
      </section>

      <section className="panel-block finale">
        <SectionTitle
          eyebrow="Ablation Story"
          title="实验分析预留位"
          description="这部分先接当前消融实验数据，等后续正式模型结果出来后，可以直接扩展成完整的数据故事页面。"
        />
        <div className="ablation-strip">
          {ablation.map((item) => (
            <article key={`${item.model_name}-${item.embedding_dim}-${item.mlp_layers}`} className="ablation-card">
              <p>{item.model_name.toUpperCase()}</p>
              <h3>{item.embedding_dim}D Embedding</h3>
              <span>Neg {item.negative_ratio} · MLP {item.mlp_layers} 层</span>
              <strong>HR {formatMetric(item.hr10)} / NDCG {formatMetric(item.ndcg10)}</strong>
            </article>
          ))}
          {bestAblation ? (
            <article className="ablation-summary">
              <p>当前最佳展示样例</p>
              <h3>{bestAblation.model_name.toUpperCase()}</h3>
              <span>{bestAblation.embedding_dim}D · {bestAblation.mlp_layers} 层</span>
              <strong>{formatMetric(bestAblation.hr10)}</strong>
            </article>
          ) : null}
        </div>
      </section>
    </div>
  );
}
