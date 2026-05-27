export default function SectionTitle({ eyebrow, title, description, action }) {
  return (
    <div className="section-title">
      <div>
        {eyebrow ? <p className="section-eyebrow">{eyebrow}</p> : null}
        <h2>{title}</h2>
        {description ? <p className="section-description">{description}</p> : null}
      </div>
      {action ? <div className="section-action">{action}</div> : null}
    </div>
  );
}
