import DOMPurify from 'dompurify'

export function sanitize(html: string) {
  return DOMPurify.sanitize(html, {
    ALLOWED_TAGS: ['p','h1','h2','h3','strong','em','b','i','u','a','ul','ol','li','blockquote','span','br'],
    ALLOWED_ATTR: ['href','style']
  })
}
