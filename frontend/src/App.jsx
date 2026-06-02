import { useEffect, useMemo, useState } from 'react';
import {
  createUser,
  deleteUserRating,
  fetchAlgorithms,
  fetchHealth,
  fetchHistory,
  fetchHotMovieBoards,
  fetchHotMovies,
  fetchMovieDetail,
  fetchMovieRatings,
  fetchPreferenceProfile,
  fetchRecommendations,
  fetchUsers,
  fetchUserMovieRating,
  saveUserRating,
  searchMovies,
  updateUserRating,
} from './lib/api';
import MoviePosterCard from './components/MoviePosterCard';
import SectionTitle from './components/SectionTitle';
import StatCard from './components/StatCard';

const LIMIT_OPTIONS = [4, 6, 8];
const TOTAL_BOARD_KEY = '__total__';
const COMMENT_PAGE_SIZE = 8;
const PREFERENCE_WINDOWS = [
  { key: 'all', label: '全部' },
  { key: 'year', label: '近一年' },
  { key: 'quarter', label: '近90天' },
  { key: 'month', label: '近30天' },
];
const CHART_COLORS = ['#ffc455', '#62d8ff', '#8ff2bf', '#ff7c73', '#b49cff', '#f2d17d'];

function getRouteMovieId(pathname) {
  const match = pathname.match(/^\/movies\/(\d+)/);
  return match ? match[1] : '';
}

function isAdminRoute(pathname) {
  return pathname === '/admin';
}

function commentText(record) {
  return record?.comment?.trim() || '空评论';
}

export default function App() {
  const [routePath, setRoutePath] = useState(window.location.pathname);
  const [health, setHealth] = useState(null);
  const [users, setUsers] = useState([]);
  const [algorithms, setAlgorithms] = useState([]);
  const [hotMovies, setHotMovies] = useState([]);
  const [hotMovieBoards, setHotMovieBoards] = useState([]);
  const [selectedHotBoard, setSelectedHotBoard] = useState(TOTAL_BOARD_KEY);
  const [recommendations, setRecommendations] = useState([]);
  const [history, setHistory] = useState([]);
  const [preferenceProfile, setPreferenceProfile] = useState(null);
  const [selectedPreferenceWindow, setSelectedPreferenceWindow] = useState('all');
  const [selectedMovie, setSelectedMovie] = useState(null);
  const [movieDetail, setMovieDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [selectedUser, setSelectedUser] = useState('');
  const [selectedAlgorithm, setSelectedAlgorithm] = useState('');
  const [selectedLimit, setSelectedLimit] = useState(6);
  const [userDataVersion, setUserDataVersion] = useState(0);
  const [newUserForm, setNewUserForm] = useState({ username: '', age: '', gender: 'U', occupation: '' });
  const [creatingUser, setCreatingUser] = useState(false);
  const [createUserMessage, setCreateUserMessage] = useState('');
  const [homeMovieQuery, setHomeMovieQuery] = useState('');
  const [homeMovieResults, setHomeMovieResults] = useState([]);
  const [homeSearchMessage, setHomeSearchMessage] = useState('');
  const [homeSearching, setHomeSearching] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const routeMovieId = getRouteMovieId(routePath);
  const adminRoute = isAdminRoute(routePath);

  useEffect(() => {
    function syncRoute() {
      setRoutePath(window.location.pathname);
    }
    window.addEventListener('popstate', syncRoute);
    return () => window.removeEventListener('popstate', syncRoute);
  }, []);

  useEffect(() => {
    let disposed = false;

    async function bootstrap() {
      setLoading(true);
      setError('');
      try {
        const [healthRes, usersRes, algoRes, hotRes, hotBoardsRes] = await Promise.all([
          fetchHealth(),
          fetchUsers(),
          fetchAlgorithms(),
          fetchHotMovies(10),
          fetchHotMovieBoards(10, 8),
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
        setHotMovieBoards(hotBoardsRes.items || []);

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
        const [recommendationRes, historyRes, preferenceRes] = await Promise.all([
          fetchRecommendations(selectedUser, selectedAlgorithm, selectedLimit),
          fetchHistory(selectedUser),
          fetchPreferenceProfile(selectedUser, selectedPreferenceWindow),
        ]);

        if (disposed) {
          return;
        }

        setRecommendations(recommendationRes.items || []);
        setHistory(historyRes.items || []);
        setPreferenceProfile(preferenceRes || null);
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
  }, [selectedUser, selectedAlgorithm, selectedLimit, selectedPreferenceWindow, userDataVersion]);

  const selectedUserProfile = useMemo(
    () => users.find((user) => String(user.user_id) === String(selectedUser)),
    [users, selectedUser]
  );

  const selectedAlgorithmMeta = useMemo(
    () => algorithms.find((item) => item.name === selectedAlgorithm),
    [algorithms, selectedAlgorithm]
  );

  const allHotBoards = useMemo(
    () => [
      {
        genre: TOTAL_BOARD_KEY,
        label: '总榜',
        total_ratings: hotMovies.reduce((total, movie) => total + (movie.rating_count || 0), 0),
        items: hotMovies,
      },
      ...hotMovieBoards.map((board) => ({ ...board, label: board.genre })),
    ],
    [hotMovies, hotMovieBoards]
  );
  const activeHotBoard = allHotBoards.find((board) => board.genre === selectedHotBoard) || allHotBoards[0];

  async function handleMovieSelect(movie) {
    setSelectedMovie(movie);
    window.history.pushState({}, '', `/movies/${movie.movie_id}`);
    setRoutePath(window.location.pathname);
  }

  async function handleHomeMovieSearch(event) {
    event.preventDefault();
    const query = homeMovieQuery.trim();
    if (!query) {
      setHomeSearchMessage('请输入电影名、年份或类型关键词。');
      return;
    }
    setHomeSearching(true);
    setHomeSearchMessage('');
    setError('');
    try {
      const result = await searchMovies(query, 18);
      setHomeMovieResults(result.items || []);
      if (!result.items?.length) {
        setHomeSearchMessage('没有找到匹配电影，可以换一个更宽泛的关键词。');
      }
    } catch (err) {
      setError(err.message || String(err));
    } finally {
      setHomeSearching(false);
    }
  }

  useEffect(() => {
    let disposed = false;

    async function loadMovieDetail() {
      if (!routeMovieId) {
        setMovieDetail(null);
        setDetailLoading(false);
        return;
      }

      setDetailLoading(true);
      setError('');
      try {
        const detail = await fetchMovieDetail(routeMovieId);
        if (!disposed) {
          setMovieDetail(detail);
        }
      } catch (err) {
        if (!disposed) {
          setError(err.message || String(err));
        }
      } finally {
        if (!disposed) {
          setDetailLoading(false);
        }
      }
    }

    loadMovieDetail();
    return () => {
      disposed = true;
    };
  }, [routeMovieId, userDataVersion]);

  if (routeMovieId) {
    return (
      <MovieDetailPage
        movie={movieDetail || selectedMovie}
        loading={detailLoading}
        error={error}
        users={users}
        selectedUser={selectedUser}
        onRatingChanged={() => setUserDataVersion((version) => version + 1)}
        setError={setError}
        onBack={() => {
          window.history.pushState({}, '', '/');
          setRoutePath(window.location.pathname);
          setSelectedMovie(null);
          setMovieDetail(null);
        }}
      />
    );
  }

  if (adminRoute) {
    return (
      <AdminPage
        users={users}
        setUsers={setUsers}
        selectedUser={selectedUser}
        setSelectedUser={setSelectedUser}
        algorithms={algorithms}
        selectedAlgorithm={selectedAlgorithm}
        setSelectedAlgorithm={setSelectedAlgorithm}
        selectedLimit={selectedLimit}
        setSelectedLimit={setSelectedLimit}
        selectedAlgorithmMeta={selectedAlgorithmMeta}
        selectedUserProfile={selectedUserProfile}
        health={health}
        newUserForm={newUserForm}
        setNewUserForm={setNewUserForm}
        creatingUser={creatingUser}
        setCreatingUser={setCreatingUser}
        createUserMessage={createUserMessage}
        setCreateUserMessage={setCreateUserMessage}
        setError={setError}
        onBack={() => {
          window.history.pushState({}, '', '/');
          setRoutePath(window.location.pathname);
        }}
      />
    );
  }

  return (
    <div className="app-shell">
      <header className="hero-frame">
        <div className="hero-copy">
          <p className="hero-kicker">Cinematic Recommendation Studio</p>
          <h1>把推荐系统做成一场有质感的电影首映礼。</h1>
          <p className="hero-text">
            这个前端项目直接消费你们已经搭好的后端 API，用更完整的视觉语言把个性化推荐、热门影片、历史偏好和电影详情串成一条答辩叙事线。
          </p>
          <div className="hero-actions">
            <a href="http://127.0.0.1:8000/docs" target="_blank" rel="noreferrer">
              查看 API 文档
            </a>
            <button
              type="button"
              className="link-pill"
              onClick={() => {
                window.history.pushState({}, '', '/admin');
                setRoutePath(window.location.pathname);
              }}
            >
              推荐后台
            </button>
            <span>数据源：{health?.data_source?.toUpperCase() || '-'}</span>
          </div>
        </div>
        <div className="hero-stage">
          <div className="spotlight-card primary current-user-card">
            <div className="current-user-head">
              <div>
                <span>Current User</span>
                <strong>{selectedUserProfile?.username || 'Loading'}</strong>
              </div>
              <label className="mini-user-switch">
                <span>切换</span>
                <select value={selectedUser} onChange={(event) => setSelectedUser(event.target.value)}>
                  {users.map((user) => (
                    <option key={user.user_id} value={user.user_id}>
                      {user.user_id} - {user.username}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <p>{selectedUserProfile ? `${selectedUserProfile.occupation || '未知职业'} · ${selectedUserProfile.age || '-'} 岁` : '正在读取用户画像'}</p>
          </div>
          <div className="spotlight-card secondary">
            <div className="current-user-head">
              <div>
                <span>Current Algorithm</span>
                <strong>{selectedAlgorithmMeta?.name || 'Loading'}</strong>
              </div>
              <label className="mini-user-switch">
                <span>切换</span>
                <select value={selectedAlgorithm} onChange={(event) => setSelectedAlgorithm(event.target.value)}>
                  {algorithms.map((algorithm) => (
                    <option key={algorithm.name} value={algorithm.name}>
                      {algorithm.name}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <p>{selectedAlgorithmMeta?.description || '等待算法信息'}</p>
          </div>
        </div>
      </header>

      <section className="control-board home-search-board">
        <SectionTitle
          eyebrow="Movie Search"
          title="电影搜索"
          description="在首页宽松匹配电影名、年份或类型，选中结果后进入独立详情页维护评分和评论。"
        />
        <form className="movie-search-row home-search-row" onSubmit={handleHomeMovieSearch}>
          <input
            value={homeMovieQuery}
            onChange={(event) => setHomeMovieQuery(event.target.value)}
            placeholder="例如 matrix / toy story / 1994 / comedy"
          />
          <button type="submit" disabled={homeSearching}>{homeSearching ? '搜索中...' : '搜索'}</button>
        </form>
        {homeSearchMessage ? <p className="admin-message">{homeSearchMessage}</p> : null}
        <div className="movie-search-results home-search-results">
          {homeMovieResults.map((movie) => (
            <button type="button" key={movie.movie_id} onClick={() => handleMovieSelect(movie)}>
              <img src={movie.poster_url} alt="" />
              <span>
                <strong>{movie.title}</strong>
                <em>{movie.year || '-'} · {(movie.genres || []).join(' / ')}</em>
              </span>
            </button>
          ))}
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

      <section className="layout-grid recommendation-layout">
        <div className="panel-block wide recommendation-panel">
          <SectionTitle
            eyebrow="Top Picks"
            title="个性化推荐结果"
            description={selectedAlgorithmMeta?.description || '当前选中算法的推荐结果会展示在这里。'}
          />
          <div className="poster-grid">
            {recommendations.map((movie, index) => (
              <MoviePosterCard
                key={`${movie.movie_id}-${selectedAlgorithm}`}
                movie={movie}
                index={index}
                onSelect={handleMovieSelect}
              />
            ))}
            {!recommendations.length && !loading ? <div className="empty-card">当前没有可展示的推荐结果。</div> : null}
          </div>
          <div className="preference-embedded">
            <SectionTitle
              eyebrow="User Taste"
              title="历史偏好"
              description="按不同时间窗口查看用户的类型、标签和相似用户偏好，用来解释上方推荐结果。"
            />
            <PreferenceProfilePanel
              profile={preferenceProfile}
              history={history}
              recommendations={recommendations}
              algorithm={selectedAlgorithm}
              selectedWindow={selectedPreferenceWindow}
              onWindowChange={setSelectedPreferenceWindow}
              loading={loading}
            />
          </div>
        </div>
      </section>

      <section className="panel-block hot-board-panel">
          <SectionTitle
            eyebrow="Homepage Shelf"
            title="热门榜单"
            description="用评分记录数衡量热度；可以切换总榜和不同电影主类型分榜，平均分只作为辅助参考。"
          />
          <div className="hot-board-tabs">
            {allHotBoards.map((board) => (
              <button
                type="button"
                key={board.genre}
                className={board.genre === selectedHotBoard ? 'active' : ''}
                onClick={() => setSelectedHotBoard(board.genre)}
              >
                {board.label}
              </button>
            ))}
          </div>
          {activeHotBoard ? (
            <article className="hot-board-card featured">
              <div className="hot-board-head">
                <div>
                  <span className="hot-board-kicker">{activeHotBoard.genre === TOTAL_BOARD_KEY ? 'Overall Chart' : 'Genre Chart'}</span>
                  <h3>{activeHotBoard.label}</h3>
                </div>
                <span>{activeHotBoard.total_ratings} 条评分</span>
              </div>
              <div className="hot-rank-list featured">
                {activeHotBoard.items.map((movie, index) => (
                  <button type="button" key={`hot-${activeHotBoard.genre}-${movie.movie_id}`} onClick={() => handleMovieSelect(movie)}>
                    <strong>{index + 1}</strong>
                    <img src={movie.poster_url} alt="" />
                    <span>
                      <b>{movie.title}</b>
                      <em>{(movie.genres || []).join(' / ')}</em>
                    </span>
                    <i>{movie.rating_count} 评 · {Number(movie.average_rating || 0).toFixed(1)}</i>
                  </button>
                ))}
              </div>
            </article>
          ) : null}
          {!allHotBoards.length && !loading ? <div className="empty-card">暂无热门榜单数据。</div> : null}
      </section>
    </div>
  );
}

function PreferenceProfilePanel({ profile, history, recommendations, algorithm, selectedWindow, onWindowChange, loading }) {
  const topGenres = profile?.genres || [];
  const authoredTags = profile?.authored_tags || [];
  const movieTags = profile?.movie_tags || [];
  const similarUsers = profile?.similar_users || [];
  const topHistory = profile?.top_history?.length ? profile.top_history : history.slice(0, 5);
  const maxGenreScore = Math.max(...topGenres.map((item) => item.score || 0), 1);
  const recommendedMovies = recommendations || [];
  const recommendedGenreCounts = recommendedMovies.reduce((counts, movie) => {
    (movie.genres || []).forEach((genre) => {
      counts[genre] = (counts[genre] || 0) + 1;
    });
    return counts;
  }, {});
  const maxRecommendationSupport = Math.max(
    ...recommendedMovies.map((movie) => Number(movie.support || movie.rating_count || 0)),
    1
  );
  const genrePieData = topGenres.slice(0, 6);
  const genrePieTotal = genrePieData.reduce((total, item) => total + (item.score || 0), 0);
  const genrePieStyle = {
    background: genrePieTotal
      ? `conic-gradient(${genrePieData.reduce((segments, item, index) => {
          const start = segments.cursor;
          const end = start + ((item.score || 0) / genrePieTotal) * 100;
          segments.parts.push(`${CHART_COLORS[index % CHART_COLORS.length]} ${start}% ${end}%`);
          segments.cursor = end;
          return segments;
        }, { cursor: 0, parts: [] }).parts.join(', ')})`
      : 'rgba(255,255,255,0.06)',
  };
  const ratingColumns = [5, 4, 3, 2, 1].map((score) => ({
    score,
    count: topHistory.filter((movie) => Math.round(Number(movie.rating || 0)) === score).length,
  }));
  const maxRatingColumn = Math.max(...ratingColumns.map((item) => item.count), 1);
  const recommendedGenreData = Object.entries(recommendedGenreCounts)
    .map(([label, count]) => ({ label, count }))
    .sort((left, right) => right.count - left.count || left.label.localeCompare(right.label))
    .slice(0, 6);
  const maxRecommendedGenreCount = Math.max(...recommendedGenreData.map((item) => item.count), 1);
  const modeCopy = {
    content_based: {
      label: '类型画像视图',
      description: '当前算法主要依赖电影主类型，因此优先展示类型强度和标签语义。',
    },
    user_cf: {
      label: '相似用户视图',
      description: '当前算法依赖用户邻域，因此优先展示相似用户和共同偏好的历史线索。',
    },
    popularity: {
      label: '热度校准视图',
      description: '当前算法偏向全站热度，这里用用户历史高分片和热门候选做对照。',
    },
  };
  const activeMode = modeCopy[algorithm] || {
    label: '偏好解释视图',
    description: '根据当前算法展示用户历史偏好的解释线索。',
  };

  const chartOverviewSection = (
    <section className="chart-overview" key="chart-overview">
      <div className="chart-relation-map">
        <span>历史评分与标签</span>
        <i />
        <span>用户偏好画像</span>
        <i />
        <span>算法解释图</span>
        <i />
        <span>推荐结果</span>
      </div>

      <article className="chart-card pie-card">
        <h3>类型占比</h3>
        <p>由历史评分聚合而来，是内容算法和推荐类型构成的输入画像。</p>
        <div className="pie-layout">
          <div className="genre-pie" style={genrePieStyle}><span /></div>
          <div className="pie-legend">
            {genrePieData.map((item, index) => (
              <span key={item.label}>
                <i style={{ background: CHART_COLORS[index % CHART_COLORS.length] }} />
                {item.label}
              </span>
            ))}
            {!genrePieData.length ? <em>暂无类型数据</em> : null}
          </div>
        </div>
      </article>

      <article className="chart-card column-card">
        <h3>历史评分柱状图</h3>
        <p>显示用户评分习惯；高分历史会影响类型权重和相似用户匹配。</p>
        <div className="rating-columns">
          {ratingColumns.map((item) => (
            <div key={item.score}>
              <i style={{ height: `${Math.max((item.count / maxRatingColumn) * 100, item.count ? 12 : 2)}%` }} />
              <span>{item.score}星</span>
              <em>{item.count}</em>
            </div>
          ))}
        </div>
      </article>

      <article className="chart-card rec-genre-card">
        <h3>推荐类型构成</h3>
        <p>与类型占比对照，用来观察推荐结果是否跟用户画像保持一致。</p>
        <div className="rec-genre-bars">
          {recommendedGenreData.map((item) => (
            <div key={item.label}>
              <span>{item.label}</span>
              <b><i style={{ width: `${Math.max((item.count / maxRecommendedGenreCount) * 100, 8)}%` }} /></b>
              <em>{item.count}</em>
            </div>
          ))}
          {!recommendedGenreData.length ? <div className="empty-card">暂无推荐类型数据。</div> : null}
        </div>
      </article>
    </section>
  );

  const principleSection = (
    <section className={`algorithm-principle principle-${algorithm || 'default'}`} key="principle">
      <div className="principle-head">
        <div>
          <span>算法原理可视化</span>
          <strong>{activeMode.label}</strong>
        </div>
        <p>{activeMode.description}</p>
      </div>

      {algorithm === 'content_based' ? (
        <>
        <p className="principle-caption">读取“类型占比”作为用户画像，再检查推荐电影是否命中这些类型。</p>
        <div className="genre-match-matrix">
          {topGenres.slice(0, 6).map((genre) => {
            const hitCount = recommendedGenreCounts[genre.label] || 0;
            return (
              <article key={genre.label}>
                <span>{genre.label}</span>
                <div className="matrix-track">
                  <i style={{ width: `${Math.max((genre.score / maxGenreScore) * 100, 8)}%` }} />
                </div>
                <em>{hitCount} 个推荐命中</em>
              </article>
            );
          })}
          {!topGenres.length ? <div className="empty-card">暂无可用于内容匹配的类型画像。</div> : null}
        </div>
        </>
      ) : null}

      {algorithm === 'user_cf' ? (
        <>
        <p className="principle-caption">先找历史行为相似的用户，再从这些用户喜欢的电影中形成推荐候选。</p>
        <div className="cf-flow">
          <div className="cf-node self">当前用户</div>
          <div className="cf-column">
            {similarUsers.slice(0, 4).map((user) => (
              <div className="cf-node neighbor" key={user.user_id}>
                <strong>{user.username}</strong>
                <span>{Math.round((user.similarity || 0) * 100)}% 相似</span>
              </div>
            ))}
          </div>
          <div className="cf-column movies">
            {recommendedMovies.slice(0, 4).map((movie) => (
              <div className="cf-node movie" key={movie.movie_id}>
                <strong>{movie.title}</strong>
                <span>{(movie.genres || []).slice(0, 2).join(' / ')}</span>
              </div>
            ))}
          </div>
          {!similarUsers.length ? <div className="empty-card">暂无足够相似用户用于邻域传播展示。</div> : null}
        </div>
        </>
      ) : null}

      {algorithm === 'popularity' ? (
        <>
        <p className="principle-caption">不强依赖个人画像，主要用全站评分支撑量解释为什么这些电影更容易被推到前面。</p>
        <div className="popularity-calibration">
          {recommendedMovies.slice(0, 6).map((movie) => {
            const support = Number(movie.support || movie.rating_count || 0);
            return (
              <article key={movie.movie_id}>
                <span>{movie.title}</span>
                <div className="popularity-track">
                  <i style={{ width: `${Math.max((support / maxRecommendationSupport) * 100, 6)}%` }} />
                </div>
                <em>{support || '-'} 条支撑</em>
              </article>
            );
          })}
          {!recommendedMovies.length ? <div className="empty-card">暂无推荐结果用于热度校准。</div> : null}
        </div>
        </>
      ) : null}

      {!['content_based', 'user_cf', 'popularity'].includes(algorithm) ? (
        <div className="empty-card">当前算法暂未配置专属解释图。</div>
      ) : null}
    </section>
  );

  const genreSection = (
    <section className="preference-section genre-viz" key="genres">
      <h3>主类型偏好</h3>
      {topGenres.length ? (
        <div className="taste-bars">
          {topGenres.slice(0, 6).map((item) => (
            <div className="taste-bar-row" key={item.label}>
              <span>{item.label}</span>
              <div><i style={{ width: `${Math.max((item.score / maxGenreScore) * 100, 8)}%` }} /></div>
              <em>{item.count} 次 · {Number(item.average_rating || 0).toFixed(1)}</em>
            </div>
          ))}
        </div>
      ) : (
        <div className="empty-card">当前时间范围内暂无类型偏好。</div>
      )}
    </section>
  );

  const authoredTagSection = (
    <section className="preference-section tag-viz" key="authored-tags">
      <h3>用户自定义标签</h3>
      {authoredTags.length ? (
        <div className="mini-tag-cloud">
          {authoredTags.map((tag) => <span key={tag.tag}>{tag.tag}<em>{tag.count}</em></span>)}
        </div>
      ) : (
        <div className="empty-card">该用户在当前时间范围内没有主动标注标签。</div>
      )}
    </section>
  );

  const movieTagSection = (
    <section className="preference-section tag-viz wide-viz" key="movie-tags">
      <h3>看过电影的自由标签合集</h3>
      {movieTags.length ? (
        <div className="mini-tag-cloud cyan">
          {movieTags.slice(0, 14).map((tag) => <span key={tag.tag}>{tag.tag}<em>{tag.count}</em></span>)}
        </div>
      ) : (
        <div className="empty-card">当前历史电影没有可聚合的用户自由文本标签。</div>
      )}
    </section>
  );

  const similarUserSection = (
    <section className="preference-section neighbor-viz" key="similar-users">
      <h3>类似用户喜好</h3>
      {similarUsers.length ? (
        <div className="similar-user-list">
          {similarUsers.map((user) => (
            <article key={user.user_id}>
              <div>
                <strong>{user.username}</strong>
                <span>ID {user.user_id} · {user.occupation || '未知职业'} · {user.rating_count} 条评分</span>
              </div>
              <em>{Math.round((user.similarity || 0) * 100)}%</em>
            </article>
          ))}
        </div>
      ) : (
        <div className="empty-card">当前时间范围内还不足以计算类似用户。</div>
      )}
    </section>
  );

  const historySection = (
    <section className="preference-section history-viz" key="history">
      <h3>{algorithm === 'popularity' ? '历史高分片对照' : '最近参与画像的电影'}</h3>
      <div className="stack-list compact">
        {topHistory.slice(0, 5).map((movie) => (
          <article key={`history-${movie.movie_id}`} className="stack-card">
            <div>
              <h3>{movie.title}</h3>
              <p>{(movie.genres || []).join(' / ')}{movie.rated_at ? ` · ${movie.rated_at}` : ''}</p>
            </div>
            <strong>{Number(movie.rating).toFixed(1)}</strong>
          </article>
        ))}
        {!topHistory.length && !loading ? <div className="empty-card">该用户暂无历史记录。</div> : null}
      </div>
    </section>
  );

  const directorSection = (
    <section className="preference-section data-viz" key="director">
      <h3>导演偏好</h3>
      <div className="data-note">
        <strong>当前数据不可用</strong>
        <p>{profile?.director_status?.reason || 'MovieLens 10M 不包含导演字段，因此不会在界面里伪造导演偏好。'}</p>
      </div>
    </section>
  );

  const orderedSections = {
    content_based: [chartOverviewSection, principleSection, genreSection, movieTagSection, authoredTagSection, historySection, similarUserSection, directorSection],
    user_cf: [chartOverviewSection, principleSection, similarUserSection, historySection, genreSection, movieTagSection, authoredTagSection, directorSection],
    popularity: [chartOverviewSection, principleSection, historySection, genreSection, movieTagSection, similarUserSection, authoredTagSection, directorSection],
  }[algorithm] || [chartOverviewSection, principleSection, genreSection, movieTagSection, authoredTagSection, similarUserSection, historySection, directorSection];

  return (
    <div className={`preference-panel algorithm-${algorithm || 'default'}`}>
      <div className="preference-tabs">
        {PREFERENCE_WINDOWS.map((item) => (
          <button
            type="button"
            key={item.key}
            className={selectedWindow === item.key ? 'active' : ''}
            onClick={() => onWindowChange(item.key)}
          >
            {item.label}
          </button>
        ))}
      </div>

      {profile ? (
        <div className="preference-summary">
          <div className="algorithm-note">
            <span>解释视图</span>
            <strong>{activeMode.label}</strong>
            <p>{activeMode.description}</p>
          </div>
          <div>
            <span>时间范围</span>
            <strong>{profile.window?.label || '全部历史'}</strong>
            <p>
              {profile.window?.since_date ? `${profile.window.since_date} 至 ${profile.window.latest_date}` : '覆盖该用户全部评分历史'}
            </p>
          </div>
          <div>
            <span>评分记录</span>
            <strong>{profile.rating_count}</strong>
            <p>{profile.rated_movie_count} 部电影参与画像计算</p>
          </div>
        </div>
      ) : null}

      {orderedSections}
    </div>
  );
}

function AdminPage({
  users,
  setUsers,
  selectedUser,
  setSelectedUser,
  algorithms,
  selectedAlgorithm,
  setSelectedAlgorithm,
  selectedLimit,
  setSelectedLimit,
  selectedAlgorithmMeta,
  selectedUserProfile,
  health,
  newUserForm,
  setNewUserForm,
  creatingUser,
  setCreatingUser,
  createUserMessage,
  setCreateUserMessage,
  setError,
  onBack,
}) {
  const [movieQuery, setMovieQuery] = useState('');
  const [movieResults, setMovieResults] = useState([]);
  const [selectedMovieForEdit, setSelectedMovieForEdit] = useState(null);
  const [ratingForm, setRatingForm] = useState({ rating: '4.0', comment: '' });
  const [ratingMessage, setRatingMessage] = useState('');
  const [movieSearchMessage, setMovieSearchMessage] = useState('');
  const [savingRating, setSavingRating] = useState(false);

  useEffect(() => {
    let disposed = false;
    async function loadSelectedRating() {
      if (!selectedUser || !selectedMovieForEdit) {
        return;
      }
      try {
        const rating = await fetchUserMovieRating(selectedUser, selectedMovieForEdit.movie_id);
        if (!disposed) {
          setRatingForm({ rating: String(rating.rating || '4.0'), comment: rating.comment || '' });
          setRatingMessage('已加载该用户现有评分，可直接修改。');
        }
      } catch {
        if (!disposed) {
          setRatingForm({ rating: '4.0', comment: '' });
          setRatingMessage('该用户还没有给这部电影评分，可新增评分和评论。');
        }
      }
    }
    loadSelectedRating();
    return () => {
      disposed = true;
    };
  }, [selectedUser, selectedMovieForEdit]);

  async function handleCreateAdminUser(event) {
    event.preventDefault();
    const username = newUserForm.username.trim();
    if (!username) {
      setCreateUserMessage('请先填写用户名。');
      return;
    }

    setCreatingUser(true);
    setCreateUserMessage('');
    setError('');
    try {
      const user = await createUser({
        username,
        age: newUserForm.age ? Number(newUserForm.age) : null,
        gender: newUserForm.gender === 'U' ? null : newUserForm.gender,
        occupation: newUserForm.occupation.trim() || null,
      });
      setUsers((current) => {
        const withoutDuplicate = current.filter((item) => String(item.user_id) !== String(user.user_id));
        return [user, ...withoutDuplicate];
      });
      setSelectedUser(String(user.user_id));
      setNewUserForm({ username: '', age: '', gender: 'U', occupation: '' });
      setCreateUserMessage(`已创建用户 ${user.username}。`);
    } catch (err) {
      setCreateUserMessage('');
      setError(err.message || String(err));
    } finally {
      setCreatingUser(false);
    }
  }

  async function handleMovieSearch(event) {
    event.preventDefault();
    const query = movieQuery.trim();
    if (!query) {
      setMovieSearchMessage('请输入电影名、年份或类型关键词。');
      return;
    }
    setMovieSearchMessage('');
    setError('');
    try {
      const result = await searchMovies(query, 24);
      setMovieResults(result.items || []);
      if (!result.items?.length) {
        setMovieSearchMessage('没有找到匹配电影，可以换一个更宽泛的关键词。');
      }
    } catch (err) {
      setError(err.message || String(err));
    }
  }

  async function handleSelectMovie(movie) {
    setSelectedMovieForEdit(movie);
    setRatingMessage('');
    setRatingForm({ rating: '4.0', comment: '' });
    if (!selectedUser) {
      return;
    }
    try {
      const rating = await fetchUserMovieRating(selectedUser, movie.movie_id);
      setRatingForm({
        rating: String(rating.rating || '4.0'),
        comment: rating.comment || '',
      });
      setRatingMessage('已加载该用户现有评分，可直接修改。');
    } catch {
      setRatingMessage('该用户还没有给这部电影评分，可新增评分和评论。');
    }
  }

  async function handleSaveRating(event) {
    event.preventDefault();
    if (!selectedUser || !selectedMovieForEdit) {
      setRatingMessage('请先选择用户和电影。');
      return;
    }

    setSavingRating(true);
    setRatingMessage('');
    setError('');
    const payload = {
      movie_id: selectedMovieForEdit.movie_id,
      rating: Number(ratingForm.rating),
      comment: ratingForm.comment.trim() || null,
    };
    try {
      let existed = true;
      try {
        await fetchUserMovieRating(selectedUser, selectedMovieForEdit.movie_id);
      } catch {
        existed = false;
      }
      if (existed) {
        await updateUserRating(selectedUser, selectedMovieForEdit.movie_id, payload);
      } else {
        await saveUserRating(selectedUser, payload);
      }
      setRatingMessage(existed ? '已更新评分和评论。' : '已新增评分和评论。');
    } catch (err) {
      setError(err.message || String(err));
    } finally {
      setSavingRating(false);
    }
  }

  async function handleDeleteRating() {
    if (!selectedUser || !selectedMovieForEdit) {
      setRatingMessage('请先选择用户和电影。');
      return;
    }
    setSavingRating(true);
    setRatingMessage('');
    setError('');
    try {
      const result = await deleteUserRating(selectedUser, selectedMovieForEdit.movie_id);
      setRatingMessage(result.deleted ? '已删除该用户对这部电影的评分。' : '该用户没有这部电影的评分记录。');
      setRatingForm({ rating: '4.0', comment: '' });
    } catch (err) {
      setError(err.message || String(err));
    } finally {
      setSavingRating(false);
    }
  }

  return (
    <div className="app-shell admin-shell">
      <div className="movie-page-nav">
        <button type="button" onClick={onBack}>返回推荐首页</button>
        <a href="http://127.0.0.1:8000/docs" target="_blank" rel="noreferrer">API 文档</a>
      </div>

      <section className="panel-block admin-hero">
        <p className="section-eyebrow">Recommendation Admin</p>
        <h1>推荐后台控制面板</h1>
        <p>管理员在这里切换演示用户、推荐算法、展示条数，也可以继续维护评分和评论数据。</p>
      </section>

      <section className="panel-block admin-card recommendation-admin-card">
        <SectionTitle
          eyebrow="Live Config"
          title="推荐设置"
          description="这些配置会影响首页的个性化推荐结果，方便管理员在后台切换答辩演示视角。"
        />
        <div className="control-grid">
          <label>
            <span>演示用户</span>
            <select value={selectedUser} onChange={(event) => setSelectedUser(event.target.value)}>
              {users.map((user) => (
                <option key={user.user_id} value={user.user_id}>
                  {user.user_id} - {user.username}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>推荐算法</span>
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
        <div className="admin-config-summary">
          <div>
            <span>当前用户</span>
            <strong>{selectedUserProfile?.username || '-'}</strong>
            <p>{selectedUserProfile ? `${selectedUserProfile.occupation || '未知职业'} · ${selectedUserProfile.age || '-'} 岁` : '等待选择用户'}</p>
          </div>
          <div>
            <span>当前算法</span>
            <strong>{selectedAlgorithmMeta?.name || '-'}</strong>
            <p>{selectedAlgorithmMeta?.description || '等待选择算法'}</p>
          </div>
          <div>
            <span>数据源</span>
            <strong>{health?.data_source?.toUpperCase() || '-'}</strong>
            <p>后台切换后，返回首页即可看到新的推荐面板状态。</p>
          </div>
        </div>
      </section>

      <section className="admin-grid">
        <form className="panel-block admin-card" onSubmit={handleCreateAdminUser}>
          <SectionTitle eyebrow="Create" title="增加用户" description="设置用户初始信息，创建后会自动选中。" />
          <div className="new-user-grid admin-form-grid">
            <label>
              <span>用户名</span>
              <input
                value={newUserForm.username}
                onChange={(event) => setNewUserForm((form) => ({ ...form, username: event.target.value }))}
                placeholder="例如 guest-demo"
              />
            </label>
            <label>
              <span>年龄</span>
              <input
                type="number"
                min="1"
                max="120"
                value={newUserForm.age}
                onChange={(event) => setNewUserForm((form) => ({ ...form, age: event.target.value }))}
                placeholder="可选"
              />
            </label>
            <label>
              <span>性别</span>
              <select
                value={newUserForm.gender}
                onChange={(event) => setNewUserForm((form) => ({ ...form, gender: event.target.value }))}
              >
                <option value="U">未设置</option>
                <option value="F">F</option>
                <option value="M">M</option>
              </select>
            </label>
            <label>
              <span>职业</span>
              <input
                value={newUserForm.occupation}
                onChange={(event) => setNewUserForm((form) => ({ ...form, occupation: event.target.value }))}
                placeholder="student / engineer / ..."
              />
            </label>
          </div>
          <button className="admin-primary-button" type="submit" disabled={creatingUser}>
            {creatingUser ? '创建中...' : '创建用户'}
          </button>
          {createUserMessage ? <p className="new-user-message">{createUserMessage}</p> : null}
        </form>

        <div className="panel-block admin-card">
          <SectionTitle eyebrow="Search" title="查找电影" description="支持标题、年份、类型的宽松匹配。" />
          <form className="movie-search-row" onSubmit={handleMovieSearch}>
            <input value={movieQuery} onChange={(event) => setMovieQuery(event.target.value)} placeholder="例如 matrix / 1994 / comedy" />
            <button type="submit">搜索</button>
          </form>
          {movieSearchMessage ? <p className="admin-message">{movieSearchMessage}</p> : null}
          <div className="movie-search-results">
            {movieResults.map((movie) => (
              <button
                type="button"
                key={movie.movie_id}
                className={selectedMovieForEdit?.movie_id === movie.movie_id ? 'active' : ''}
                onClick={() => handleSelectMovie(movie)}
              >
                <img src={movie.poster_url} alt="" />
                <span>
                  <strong>{movie.title}</strong>
                  <em>{movie.year || '-'} · {(movie.genres || []).join(' / ')}</em>
                </span>
              </button>
            ))}
          </div>
        </div>
      </section>

      <section className="panel-block admin-card rating-editor">
        <SectionTitle
          eyebrow="Create / Update / Delete"
          title="维护评分和评论"
          description="选择用户和电影后，可以新增、修改或删除该用户对该电影的评分记录。"
        />
        <form className="rating-editor-grid" onSubmit={handleSaveRating}>
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
            <span>电影</span>
            <input value={selectedMovieForEdit ? `${selectedMovieForEdit.movie_id} - ${selectedMovieForEdit.title}` : ''} readOnly placeholder="请先搜索并选择电影" />
          </label>
          <label>
            <span>评分</span>
            <input
              type="number"
              min="0.5"
              max="5"
              step="0.5"
              value={ratingForm.rating}
              onChange={(event) => setRatingForm((form) => ({ ...form, rating: event.target.value }))}
            />
          </label>
          <label className="comment-field">
            <span>评论</span>
            <textarea
              value={ratingForm.comment}
              onChange={(event) => setRatingForm((form) => ({ ...form, comment: event.target.value }))}
              placeholder="写一段用户对这部电影的评论，可选"
            />
          </label>
          <div className="rating-editor-actions">
            <button type="submit" disabled={savingRating}>{savingRating ? '保存中...' : '新增 / 修改评分'}</button>
            <button type="button" className="danger-button" disabled={savingRating} onClick={handleDeleteRating}>删除评分</button>
          </div>
        </form>
        {ratingMessage ? <p className="admin-message">{ratingMessage}</p> : null}
      </section>
    </div>
  );
}

function MovieDetailPage({ movie, loading, error, users, selectedUser, onRatingChanged, setError, onBack }) {
  const [ratingForm, setRatingForm] = useState({ rating: '4.0', comment: '' });
  const [ratingExists, setRatingExists] = useState(false);
  const [ratingMessage, setRatingMessage] = useState('');
  const [savingRating, setSavingRating] = useState(false);
  const [commentPage, setCommentPage] = useState(1);
  const [commentPageRecords, setCommentPageRecords] = useState([]);
  const [commentTotal, setCommentTotal] = useState(0);
  const [commentLoading, setCommentLoading] = useState(false);
  const [commentRefresh, setCommentRefresh] = useState(0);
  const maxDistributionCount = Math.max(...(movie?.rating_distribution || []).map((item) => item.count), 1);
  const ratingRecords = movie?.rating_records || [];
  const currentUser = users.find((user) => String(user.user_id) === String(selectedUser));
  const selectedUserRecord = ratingRecords.find((record) => String(record.user_id) === String(selectedUser));
  const currentUserCommentRecord = ratingExists
    ? selectedUserRecord || {
        record_id: `mine-${selectedUser}-${movie?.movie_id || ''}`,
        user_id: selectedUser,
        username: currentUser?.username || `user-${selectedUser}`,
        occupation: currentUser?.occupation,
        rating: Number(ratingForm.rating || 0),
        rated_at: '当前记录',
        comment: ratingForm.comment,
      }
    : null;
  const highComments = ratingRecords.filter((record) => Number(record.rating) >= 4).slice(0, 2);
  const mediumComments = ratingRecords.filter((record) => Number(record.rating) >= 2.5 && Number(record.rating) < 4).slice(0, 2);
  const lowComments = ratingRecords.filter((record) => Number(record.rating) < 2.5).slice(0, 2);
  const totalCommentPages = Math.max(Math.ceil(commentTotal / COMMENT_PAGE_SIZE), 1);

  useEffect(() => {
    let disposed = false;
    async function loadCurrentUserRating() {
      if (!movie?.movie_id || !selectedUser) {
        setRatingExists(false);
        setRatingForm({ rating: '4.0', comment: '' });
        return;
      }
      setRatingMessage('');
      try {
        const rating = await fetchUserMovieRating(selectedUser, movie.movie_id);
        if (!disposed) {
          setRatingExists(true);
          setRatingForm({ rating: String(rating.rating || '4.0'), comment: rating.comment || '' });
        }
      } catch {
        if (!disposed) {
          setRatingExists(false);
          setRatingForm({ rating: '4.0', comment: '' });
        }
      }
    }
    loadCurrentUserRating();
    return () => {
      disposed = true;
    };
  }, [movie?.movie_id, selectedUser]);

  useEffect(() => {
    setCommentPage(1);
  }, [movie?.movie_id]);

  useEffect(() => {
    let disposed = false;
    async function loadCommentPage() {
      if (!movie?.movie_id) {
        setCommentPageRecords([]);
        setCommentTotal(0);
        return;
      }
      setCommentLoading(true);
      try {
        const result = await fetchMovieRatings(movie.movie_id, COMMENT_PAGE_SIZE, (commentPage - 1) * COMMENT_PAGE_SIZE);
        if (!disposed) {
          setCommentPageRecords(result.items || []);
          setCommentTotal(result.total || 0);
        }
      } catch (err) {
        if (!disposed) {
          setError(err.message || String(err));
        }
      } finally {
        if (!disposed) {
          setCommentLoading(false);
        }
      }
    }
    loadCommentPage();
    return () => {
      disposed = true;
    };
  }, [movie?.movie_id, commentPage, commentRefresh, setError]);

  async function handleSaveDetailRating(event) {
    event.preventDefault();
    if (!movie?.movie_id || !selectedUser) {
      setRatingMessage('请先选择用户。');
      return;
    }

    setSavingRating(true);
    setRatingMessage('');
    setError('');
    const payload = {
      movie_id: movie.movie_id,
      rating: Number(ratingForm.rating),
      comment: ratingForm.comment.trim() || null,
    };

    try {
      if (ratingExists) {
        await updateUserRating(selectedUser, movie.movie_id, payload);
      } else {
        await saveUserRating(selectedUser, payload);
      }
      setRatingExists(true);
      setRatingMessage(ratingExists ? '我的评论已更新。' : '我的评论已发布。');
      setCommentRefresh((version) => version + 1);
      onRatingChanged();
    } catch (err) {
      setError(err.message || String(err));
    } finally {
      setSavingRating(false);
    }
  }

  async function handleDeleteDetailRating() {
    if (!movie?.movie_id || !selectedUser) {
      setRatingMessage('请先选择用户。');
      return;
    }

    setSavingRating(true);
    setRatingMessage('');
    setError('');
    try {
      const result = await deleteUserRating(selectedUser, movie.movie_id);
      setRatingExists(false);
      setRatingForm({ rating: '4.0', comment: '' });
      setRatingMessage(result.deleted ? '我的评论和评分已删除。' : '当前用户还没有这部电影的评分。');
      setCommentRefresh((version) => version + 1);
      onRatingChanged();
    } catch (err) {
      setError(err.message || String(err));
    } finally {
      setSavingRating(false);
    }
  }

  function renderCommentCard(record, className = '') {
    return (
      <article key={record.record_id} className={`comment-card ${className}`}>
        <div className="comment-meta">
          <div>
            <strong>{record.username}</strong>
            <span>用户 ID {record.user_id} · 职业 {record.occupation || '未知'} · {record.rated_at || '未知日期'}</span>
          </div>
          <em>{Number(record.rating).toFixed(1)}</em>
        </div>
        <p>{commentText(record)}</p>
      </article>
    );
  }

  return (
    <div className="app-shell movie-page-shell">
      <div className="movie-page-nav">
        <button type="button" onClick={onBack}>返回首页</button>
        <a href="http://127.0.0.1:8000/docs" target="_blank" rel="noreferrer">API 文档</a>
      </div>

      {error ? <section className="error-banner">电影详情加载失败：{error}</section> : null}
      {loading && !movie ? <section className="loading-banner">正在加载电影详情...</section> : null}

      {movie ? (
        <section className="panel-block movie-detail-panel standalone">
          <div className="movie-detail-layout">
            <div className="movie-detail-poster">
              <img src={movie.poster_url} alt={`${movie.title} poster`} />
            </div>
            <div className="movie-detail-main">
              <p className="section-eyebrow">Movie Detail</p>
              <h1 className="movie-detail-title">{movie.title}</h1>
              <p className="movie-detail-summary">{movie.summary || '暂无影片简介。'}</p>

              <div className="detail-stat-row">
                <div>
                  <span>平均评分</span>
                  <strong>{typeof movie.average_rating === 'number' ? movie.average_rating.toFixed(1) : '-'}</strong>
                </div>
                <div>
                  <span>评分数量</span>
                  <strong>{movie.rating_count ?? '-'}</strong>
                </div>
                <div>
                  <span>上映年份</span>
                  <strong>{movie.year || '-'}</strong>
                </div>
              </div>

              <section className="detail-section">
                <h2>电影详细标签</h2>
                <div className="genre-row detail-tags">
                  {(movie.detail_tags || []).map((tag) => (
                    <span key={`${tag.type}-${tag.label}`}>{tag.label}</span>
                  ))}
                  {!movie.detail_tags?.length ? <span>暂无标签</span> : null}
                </div>
              </section>

              <section className="detail-section">
                <h2>评分分布</h2>
                <div className="rating-distribution">
                  {(movie.rating_distribution || []).map((item) => (
                    <div className="rating-row" key={item.rating}>
                      <span>{item.rating} 星</span>
                      <div className="rating-track">
                        <i style={{ width: `${(item.count / maxDistributionCount) * 100}%` }} />
                      </div>
                      <strong>{item.count}</strong>
                    </div>
                  ))}
                </div>
              </section>

              <section className="detail-section">
                <h2>用户自由文本标签</h2>
                {movie.user_tags?.length ? (
                  <div className="user-tag-cloud">
                    {movie.user_tags.map((tag) => (
                      <span key={tag.tag}>
                        {tag.tag}
                        <em>{tag.count}</em>
                      </span>
                    ))}
                  </div>
                ) : (
                  <div className="empty-card">当前数据集没有这部电影的用户自由文本标签。`ml-1m` 只有评分；导入带 `tags.csv` 的 MovieLens 数据集后这里会自动显示。</div>
                )}
              </section>

              <section className="detail-section my-comment-section">
                <h2>我的评论</h2>
                <form className="rating-editor-grid detail-rating-editor" onSubmit={handleSaveDetailRating}>
                  <div className="current-comment-user">
                    <span>当前用户</span>
                    <strong>{currentUser ? `${currentUser.user_id} - ${currentUser.username}` : selectedUser || '-'}</strong>
                  </div>
                  <label>
                    <span>当前电影</span>
                    <input value={`${movie.movie_id} - ${movie.title}`} readOnly />
                  </label>
                  <label>
                    <span>评分</span>
                    <input
                      type="number"
                      min="0.5"
                      max="5"
                      step="0.5"
                      value={ratingForm.rating}
                      onChange={(event) => setRatingForm((form) => ({ ...form, rating: event.target.value }))}
                    />
                  </label>
                  <label className="comment-field">
                    <span>评论</span>
                    <textarea
                      value={ratingForm.comment}
                      onChange={(event) => setRatingForm((form) => ({ ...form, comment: event.target.value }))}
                      placeholder="评论可以留空；只有评分时会显示为空评论"
                    />
                  </label>
                  <div className="rating-editor-actions">
                    <button type="submit" disabled={savingRating}>{savingRating ? '保存中...' : ratingExists ? '更新我的评论' : '发布我的评论'}</button>
                    <button type="button" className="danger-button" disabled={savingRating || !ratingExists} onClick={handleDeleteDetailRating}>删除我的评论</button>
                  </div>
                </form>
                {ratingMessage ? <p className="admin-message">{ratingMessage}</p> : null}
                {currentUserCommentRecord ? (
                  <div className="my-comment-preview">
                    {renderCommentCard(currentUserCommentRecord, 'mine')}
                  </div>
                ) : null}
              </section>

              <section className="detail-section">
                <h2>精选评论</h2>
                {ratingRecords.length ? (
                  <div className="comment-buckets">
                    <CommentBucket title="高分评论" records={highComments} renderCommentCard={renderCommentCard} />
                    <CommentBucket title="中分评论" records={mediumComments} renderCommentCard={renderCommentCard} />
                    <CommentBucket title="低分评论" records={lowComments} renderCommentCard={renderCommentCard} />
                  </div>
                ) : (
                  <div className="empty-card">这部电影暂时没有评分记录。</div>
                )}
              </section>

              <section className="detail-section">
                <div className="comment-section-head">
                  <h2>全部评论</h2>
                  <span>{commentTotal || ratingRecords.length} 条评分评论</span>
                </div>
                {commentLoading ? <div className="loading-banner">正在加载评论...</div> : null}
                {commentTotal ? (
                  <>
                    <div className="comment-list">
                      {commentPageRecords.map((record) => renderCommentCard(record))}
                    </div>
                    <div className="comment-pagination">
                      <button type="button" disabled={commentPage <= 1} onClick={() => setCommentPage((page) => Math.max(page - 1, 1))}>
                        上一页
                      </button>
                      <span>{commentPage} / {totalCommentPages}</span>
                      <button type="button" disabled={commentPage >= totalCommentPages} onClick={() => setCommentPage((page) => Math.min(page + 1, totalCommentPages))}>
                        下一页
                      </button>
                    </div>
                  </>
                ) : (
                  <div className="empty-card">这部电影暂时没有评分记录。</div>
                )}
              </section>
            </div>
          </div>
        </section>
      ) : null}
    </div>
  );
}

function CommentBucket({ title, records, renderCommentCard }) {
  return (
    <div className="comment-bucket">
      <h3>{title}</h3>
      <div className="comment-list compact">
        {records.map((record) => renderCommentCard(record))}
        {!records.length ? <div className="empty-card">暂无这一档评分评论。</div> : null}
      </div>
    </div>
  );
}
