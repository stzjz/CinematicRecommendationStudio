const ARTICLE_SUFFIX_PATTERN = /,\s*(the|a|an)$/i;

export function displayMovieTitle(title) {
  const rawTitle = (title || '').trim();
  const match = rawTitle.match(ARTICLE_SUFFIX_PATTERN);
  if (!match) {
    return rawTitle;
  }
  const article = match[1];
  const body = rawTitle.replace(ARTICLE_SUFFIX_PATTERN, '').trim();
  const displayArticle = article.charAt(0).toUpperCase() + article.slice(1).toLowerCase();
  return `${displayArticle} ${body}`;
}
