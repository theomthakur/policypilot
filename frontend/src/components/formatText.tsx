import type { ReactNode } from 'react'

/** Renders the small amount of markdown models produce: **bold**. Line breaks are kept by CSS. */
export function renderInline(text: string): ReactNode[] {
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
