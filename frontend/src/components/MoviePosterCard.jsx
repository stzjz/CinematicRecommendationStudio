import { displayMovieTitle } from '../lib/movieTitle';

function buildGradient(index) {
  const gradients = [
    'linear-gradient(135deg, rgba(255, 196, 87, 0.9), rgba(255, 104, 94, 0.72))',
    'linear-gradient(135deg, rgba(74, 223, 255, 0.88), rgba(36, 110, 255, 0.72))',
    'linear-gradient(135deg, rgba(146, 255, 167, 0.84), rgba(37, 170, 131, 0.74))',
    'linear-gradient(135deg, rgba(255, 144, 211, 0.84), rgba(130, 95, 255, 0.72))',
  ];
  return gradients[index % gradients.length];
}

export default function MoviePosterCard({ movie, index, onSelect }) {
  const title = displayMovieTitle(movie.title);
  const reasonDetails = Array.isArray(movie.reason_details) ? movie.reason_details.filter(Boolean).slice(0, 3) : [];
  const backgroundStyle = movie.poster_url
    ? {
        backgroundImage: [
          'radial-gradient(circle at 18% 8%, rgba(255, 244, 218, 0.22), transparent 34%)',
          'linear-gradient(180deg, rgba(6, 11, 20, 0.00) 0%, rgba(6, 11, 20, 0.08) 48%, rgba(6, 11, 20, 0.48) 100%)',
          `url(${movie.poster_url})`,
        ].join(', '),
      }
    : {
        backgroundImage: [
          'radial-gradient(circle at 20% 10%, rgba(255, 255, 255, 0.24), transparent 32%)',
          'linear-gradient(180deg, rgba(5, 10, 18, 0.02), rgba(5, 10, 18, 0.30))',
          buildGradient(index),
        ].join(', '),
      };

  return (
    <button className="movie-poster-card" style={backgroundStyle} type="button" onClick={() => onSelect?.(movie)}>
      <div className="movie-poster-top">
        <span className="movie-chip">{movie.year || 'Movie'}</span>
        {movie.score !== undefined ? <span className="movie-chip score">{Number(movie.score).toFixed(2)}</span> : null}
      </div>
      <div className="movie-poster-copy">
        <p>{(movie.genres || []).join(' / ' )}</p>
        <h3>{title}</h3>
        <div className="recommendation-reason">
          <span>推荐理由</span>
          <p>{movie.reason || movie.summary || '为当前用户兴趣偏好挑选的候选影片。'}</p>
          {reasonDetails.length ? (
            <div className="reason-detail-list">
              {reasonDetails.map((detail) => (
                <i key={detail}>{detail}</i>
              ))}
            </div>
          ) : null}
        </div>
      </div>
    </button>
  );
}
