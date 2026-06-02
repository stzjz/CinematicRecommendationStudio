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
  const backgroundStyle = movie.poster_url
    ? { backgroundImage: `linear-gradient(180deg, rgba(4, 10, 21, 0.10), rgba(4, 10, 21, 0.48)), url(${movie.poster_url})` }
    : { backgroundImage: `linear-gradient(180deg, rgba(4, 10, 21, 0.05), rgba(4, 10, 21, 0.3)), ${buildGradient(index)}` };

  return (
    <button className="movie-poster-card" style={backgroundStyle} type="button" onClick={() => onSelect?.(movie)}>
      <div className="movie-poster-top">
        <span className="movie-chip">{movie.year || 'Movie'}</span>
        {movie.score !== undefined ? <span className="movie-chip score">{Number(movie.score).toFixed(2)}</span> : null}
      </div>
      <div className="movie-poster-copy">
        <p>{(movie.genres || []).join(' / ' )}</p>
        <h3>{movie.title}</h3>
          <p className="movie-summary">{movie.reason || movie.summary || '为当前用户兴趣偏好挑选的候选影片。'}</p>
      </div>
    </button>
  );
}
