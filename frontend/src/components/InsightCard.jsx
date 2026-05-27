export default function InsightCard({ title, lines, accent }) {
  return (
    <article className={`insight-card ${accent || ''}`.trim()}>
      <h3>{title}</h3>
      {lines.map((line) => (
        <p key={line}>{line}</p>
      ))}
    </article>
  );
}
