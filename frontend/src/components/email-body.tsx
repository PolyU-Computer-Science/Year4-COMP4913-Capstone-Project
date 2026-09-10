import { useMemo } from 'react'
import DOMPurify from 'dompurify'

interface EmailBodyProps {
  body: string
  html?: string
  emailId: string
  showImages?: boolean
}

function isHtml(body: string): boolean {
  return /<[a-z][\s\S]*>/i.test(body)
}

function renderHtml(
  html: string,
  emailId: string,
  showImages: boolean,
): string {
  const clean = DOMPurify.sanitize(html, {
    ADD_ATTR: [
      'target',
      'align',
      'border',
      'cellpadding',
      'cellspacing',
      'bgcolor',
      'width',
      'height',
    ],
  })

  const doc = new DOMParser().parseFromString(clean, 'text/html')

  doc.querySelectorAll('a').forEach((a) => {
    a.setAttribute('target', '_blank')
    a.setAttribute('rel', 'noopener noreferrer')
  })

  doc.querySelectorAll('img').forEach((img) => {
    const src = img.getAttribute('src') || ''
    if (src.startsWith('cid:')) {
      const cid = src.slice(4).trim()
      img.setAttribute(
        'src',
        `/api/emails/${emailId}/attachments/${encodeURIComponent(cid)}`,
      )
    } else if (!showImages && /^https?:\/\//i.test(src)) {
      img.setAttribute('data-src', src)
      img.removeAttribute('src')
      img.removeAttribute('srcset')
    }
  })

  return doc.body.innerHTML
}

export function EmailBody({
  body,
  html,
  emailId,
  showImages = false,
}: EmailBodyProps) {
  const markup = useMemo(() => {
    if (html && isHtml(html)) {
      return renderHtml(html, emailId, showImages)
    }
    return null
  }, [html, emailId, showImages])

  if (markup !== null) {
    return (
      <div
        className="email-body"
        dangerouslySetInnerHTML={{ __html: markup }}
      />
    )
  }

  if (!body) return null

  return (
    <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-foreground">
      {body}
    </pre>
  )
}
