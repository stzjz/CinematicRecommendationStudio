export default function StatCard({ label, value, accent }) {
  return (
    <article className={`stat-card ${accent || ''}`.trim()}>
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}
