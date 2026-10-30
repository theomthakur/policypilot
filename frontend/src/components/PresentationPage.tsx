import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
} from 'react'
import './Pages.css'

interface Slide {
  kicker: string
  title: string
  body: React.ReactNode
}

function Card({
  title,
  children,
}: {
  title: string
  children: React.ReactNode
}) {
  return (
    <div className="slide-card">
      <strong>{title}</strong>
      <p>{children}</p>
    </div>
  )
}

function Steps({ items }: { items: [string, string][] }) {
  return (
    <ol className="slide-steps">
      {items.map(([title, detail], index) => (
        <li key={title}>
          <span>{index + 1}</span>
          <strong>{title}</strong>
          <em>{detail}</em>
        </li>
      ))}
    </ol>
  )
}

const slides: Slide[] = [
  {
    kicker: 'PolicyPilot',
    title: 'Ask about your policies. Get an answer you can check.',
    body: (
      <>
        <p className="slide-lead">
          An assistant that reads policy documents, answers in plain language,
          and shows the exact page behind every claim.
        </p>
        <div className="slide-cards">
          <Card title="Cites the page">
            Every claim carries a quote and a page number.
          </Card>
          <Card title="Asks when unsure">
            If the answer depends on something you did not say, it asks.
          </Card>
          <Card title="Says when it does not know">
            No invented answers and no invented citations.
          </Card>
        </div>
      </>
    ),
  },
  {
    kicker: 'How it works',
    title: 'One question, six steps.',
    body: (
      <Steps
        items={[
          ['Understand', 'It breaks the question into what it needs to find.'],
          ['Search', 'It looks through every document for the best passages.'],
          [
            'Judge',
            'Is this enough? If not, it searches again with different words.',
          ],
          [
            'Ask if unsure',
            'If the answer depends on something you did not say, it asks you.',
          ],
          ['Answer', 'A short answer, with the quote and page for each claim.'],
          [
            'Check',
            'Each quote must appear word for word on that page, or the claim is removed.',
          ],
        ]}
      />
    ),
  },
  {
    kicker: 'How it is built',
    title: 'Two flows, one database.',
    body: (
      <div className="slide-cards">
        <Card title="Documents in">
          Each PDF is parsed page by page, cut into 200-token chunks, embedded
          locally and indexed in PostgreSQL for meaning and keyword search.
        </Card>
        <Card title="Questions in">
          An API and an agent loop with four read-only tools. Search is hybrid,
          and every quote is checked before it is shown.
        </Card>
        <Card title="Where it runs">
          Docker Compose, and Kubernetes tested on kind. An OpenShift overlay is
          written but not yet run on a real cluster. The System design page
          shows the full flow.
        </Card>
      </div>
    ),
  },
  {
    kicker: 'Does it work?',
    title: 'Tested on 30 questions, with the misses shown.',
    body: (
      <>
        <div className="slide-cards">
          <Card title="Original 11 questions">
            The assistant passed 9. The simple one-search version passed 4 of 9.
          </Card>
          <Card title="9 new questions">
            The assistant passed 9. The simple version passed 5 of 7.
          </Card>
          <Card title="10 older held-out questions">
            The assistant passed 6. The simple version passed 5 of 9.
          </Card>
        </div>
        <p className="slide-note">
          One run each. The newer sets helped guide fixes, so they are not blind
          tests. It still misses some follow-up and conflicting-policy
          questions.
        </p>
      </>
    ),
  },
  {
    kicker: 'What is next',
    title: 'Ready to share, honest about what is left.',
    body: (
      <div className="slide-cards">
        <Card title="Working">
          Private sessions with saved history, verified citations, a live
          activity view and a one-command local setup.
        </Card>
        <Card title="Not solved yet">
          Asking the right clarifying question every time, always spotting a
          replaced policy, and finishing follow-ups within the search limit.
        </Card>
        <Card title="If it grew">
          A public deployment, a run on a real OpenShift cluster, monitoring,
          and section-aware chunking.
        </Card>
      </div>
    ),
  },
]

export function PresentationPage({ onBack }: { onBack: () => void }) {
  const [index, setIndex] = useState(0)
  const [full, setFull] = useState(false)
  const deck = useRef<HTMLElement>(null)
  const slideRef = useRef<HTMLElement>(null)
  const [controlsVisible, setControlsVisible] = useState(true)

  const go = useCallback(
    (delta: number) =>
      setIndex((current) =>
        Math.min(slides.length - 1, Math.max(0, current + delta)),
      ),
    [],
  )
  const toggleFullscreen = useCallback(() => {
    if (document.fullscreenElement) void document.exitFullscreen()
    else void deck.current?.requestFullscreen?.()
  }, [])

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (
        event.key === 'ArrowRight' ||
        event.key === ' ' ||
        event.key === 'PageDown'
      ) {
        event.preventDefault()
        go(1)
      } else if (event.key === 'ArrowLeft' || event.key === 'PageUp') {
        go(-1)
      } else if (event.key.toLowerCase() === 'f') {
        toggleFullscreen()
      }
    }
    const onChange = () => setFull(Boolean(document.fullscreenElement))
    window.addEventListener('keydown', onKey)
    document.addEventListener('fullscreenchange', onChange)
    return () => {
      window.removeEventListener('keydown', onKey)
      document.removeEventListener('fullscreenchange', onChange)
    }
  }, [go, toggleFullscreen])

  // Every slide must fit the screen it is shown on, in a window or in fullscreen: if the content is taller
  // than the slide, shrink the text until it fits (never below a readable minimum).
  useLayoutEffect(() => {
    const element = slideRef.current
    if (!element) return
    const fit = () => {
      element.style.fontSize = ''
      let size = parseFloat(getComputedStyle(element).fontSize)
      for (let step = 0; step < 40; step += 1) {
        if (element.scrollHeight <= element.clientHeight + 1 || size <= 11)
          break
        size *= 0.94
        element.style.fontSize = `${size}px`
      }
    }
    fit()
    const observer = new ResizeObserver(fit)
    observer.observe(element)
    return () => observer.disconnect()
  }, [index, full])

  // In fullscreen the controls fade away and return when the mouse moves, so they never sit over a slide.
  useEffect(() => {
    if (!full) {
      setControlsVisible(true)
      return
    }
    let timer = window.setTimeout(() => setControlsVisible(false), 2500)
    const wake = () => {
      setControlsVisible(true)
      window.clearTimeout(timer)
      timer = window.setTimeout(() => setControlsVisible(false), 2500)
    }
    window.addEventListener('mousemove', wake)
    window.addEventListener('keydown', wake)
    return () => {
      window.clearTimeout(timer)
      window.removeEventListener('mousemove', wake)
      window.removeEventListener('keydown', wake)
    }
  }, [full])

  const slide = slides[index]
  const pad = (n: number) => String(n).padStart(2, '0')
  return (
    <main
      className={`deck${full ? ' deck-full' : ''}${controlsVisible ? '' : ' controls-hidden'}`}
      ref={deck}
    >
      <div className="deck-bar">
        {!full && (
          <button className="page-back" type="button" onClick={onBack}>
            <span aria-hidden="true">←</span> Back to workspace
          </button>
        )}
        <span className="deck-hint">
          ← → or Space to move · F for fullscreen
        </span>
        <button className="page-back" type="button" onClick={toggleFullscreen}>
          {full ? 'Exit fullscreen' : 'Fullscreen'}
        </button>
      </div>
      <section
        className="deck-slide"
        ref={slideRef}
        aria-live="polite"
        aria-label={`Slide ${index + 1} of ${slides.length}`}
      >
        <div className="slide-inner">
          <p className="eyebrow">{slide.kicker}</p>
          <h1>{slide.title}</h1>
          {slide.body}
        </div>
      </section>
      <footer className="deck-foot">
        <button
          type="button"
          onClick={() => go(-1)}
          disabled={index === 0}
          aria-label="Previous slide"
        >
          ←
        </button>
        <span>
          PolicyPilot · {pad(index + 1)} / {pad(slides.length)}
        </span>
        <button
          type="button"
          onClick={() => go(1)}
          disabled={index === slides.length - 1}
          aria-label="Next slide"
        >
          →
        </button>
      </footer>
    </main>
  )
}
