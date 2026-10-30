import type { ReactNode } from 'react'

/** Renders the small amount of markdown models produce: **bold**. Line breaks are kept by CSS. */
function renderInline(text: string): ReactNode[] {
  return text
    .split(/(\*\*[^*]+\*\*)/g)
    .map((part, index) =>
      part.startsWith('**') && part.endsWith('**') && part.length > 4 ? (
        <strong key={index}>{part.slice(2, -2)}</strong>
      ) : (
        part
      ),
    )
}

/** Paragraphs and bullet lists ("- item" or "1. item"), with **bold** inside. */
export function RichText({ text }: { text: string }) {
  const blocks: ReactNode[] = []
  let bullets: string[] = []
  const flush = () => {
    if (bullets.length === 0) return
    const items = bullets
    blocks.push(
      <ul key={`list-${blocks.length}`}>
        {items.map((item, index) => (
          <li key={index}>{renderInline(item)}</li>
        ))}
      </ul>,
    )
    bullets = []
  }
  text.split('\n').forEach((line) => {
    const bullet = line.match(/^\s*(?:[-*\u2022]|\d+\.)\s+(.*)$/)
    if (bullet) {
      bullets.push(bullet[1])
      return
    }
    flush()
    if (line.trim())
      blocks.push(<p key={`p-${blocks.length}`}>{renderInline(line)}</p>)
  })
  flush()
  return <>{blocks}</>
}
