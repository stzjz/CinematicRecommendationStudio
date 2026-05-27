from html import escape

PALETTES = [
    ("#1f304a", "#f9b35b", "#f7efe0"),
    ("#0f4c81", "#f25f5c", "#f7f3ea"),
    ("#2d3142", "#69dc9e", "#f3efe6"),
    ("#4c2a85", "#f6c667", "#fcf8f2"),
    ("#003049", "#d62828", "#f8f1e7"),
    ("#264653", "#e9c46a", "#f7f0df"),
]


def wrap_title(title, max_len=16):
    words = title.split()
    lines = []
    current = []
    size = 0
    for word in words:
        next_size = size + len(word) + (1 if current else 0)
        if current and next_size > max_len:
            lines.append(" ".join(current))
            current = [word]
            size = len(word)
        else:
            current.append(word)
            size = next_size
    if current:
        lines.append(" ".join(current))
    return lines[:4]


def build_poster_svg(movie):
    movie_id = movie["movie_id"]
    bg, accent, text = PALETTES[movie_id % len(PALETTES)]
    lines = wrap_title(movie["title"])
    genres = " / ".join(movie.get("genres", [])[:3])
    summary = escape(movie.get("summary", ""))
    title_svg = []
    base_y = 340
    for idx, line in enumerate(lines):
        title_svg.append(
            '<text x="56" y="{y}" fill="{text}" font-size="54" font-family="Georgia, serif" font-weight="700">{line}</text>'.format(
                y=base_y + idx * 64,
                text=text,
                line=escape(line),
            )
        )
    title_block = "\n".join(title_svg)
    return """<svg xmlns="http://www.w3.org/2000/svg" width="600" height="900" viewBox="0 0 600 900">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{bg}" />
      <stop offset="100%" stop-color="#0a1020" />
    </linearGradient>
    <radialGradient id="glow" cx="80%" cy="20%" r="60%">
      <stop offset="0%" stop-color="{accent}" stop-opacity="0.45" />
      <stop offset="100%" stop-color="{accent}" stop-opacity="0" />
    </radialGradient>
  </defs>
  <rect width="600" height="900" fill="url(#bg)" rx="30" />
  <rect width="600" height="900" fill="url(#glow)" rx="30" />
  <circle cx="520" cy="110" r="120" fill="{accent}" opacity="0.14" />
  <circle cx="90" cy="780" r="170" fill="{accent}" opacity="0.08" />
  <rect x="44" y="48" width="170" height="36" rx="18" fill="rgba(255,255,255,0.08)" />
  <text x="64" y="73" fill="{accent}" font-size="18" font-family="Arial, sans-serif" letter-spacing="2">CINEMATCH</text>
  <text x="56" y="150" fill="{text}" font-size="20" font-family="Arial, sans-serif" opacity="0.7">{genres}</text>
  <text x="56" y="220" fill="{accent}" font-size="96" font-family="Georgia, serif" font-weight="700">{year}</text>
  {title_block}
  <rect x="56" y="694" width="488" height="1" fill="rgba(255,255,255,0.18)" />
  <foreignObject x="56" y="724" width="488" height="110">
    <div xmlns="http://www.w3.org/1999/xhtml" style="color:{text};font-family:Arial,sans-serif;font-size:24px;line-height:1.45;opacity:0.9;">
      {summary}
    </div>
  </foreignObject>
</svg>""".format(
        bg=bg,
        accent=accent,
        text=text,
        genres=escape(genres),
        year=movie.get("year", ""),
        title_block=title_block,
        summary=summary,
    )
