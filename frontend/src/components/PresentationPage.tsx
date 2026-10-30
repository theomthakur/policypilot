import { useCallback, useEffect, useRef, useState } from 'react'
import { evaluationCases } from '../data/evaluation'
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

const agentPassed = evaluationCases.filter((c) => c.agent === 'pass').length
const simpleCases = evaluationCases.filter((c) => c.baseline !== 'n/a')
const simplePassed = simpleCases.filter((c) => c.baseline === 'pass').length

const slides: Slide[] = [
  {
    kicker: 'PolicyPilot',
    title: 'Ask a question about your policies. Get an answer you can check.',
    body: (
      <p className="slide-lead">
        An assistant that reads policy documents, answers in plain language, and
        shows the exact page behind every claim.
      </p>
    ),
  },
  {
    kicker: 'The problem',
    title:
      'Policies are long, and an answer is only useful if you can trust it.',
    body: (
      <div className="slide-cards">
        <Card title="Hard to find">
          The answer is on one page of one document, among dozens of pages.
        </Card>
        <Card title="Depends on who asks">
          Students, staff and guests can follow different rules for the same
          question.
        </Card>
        <Card title="Rules get replaced">
          An old policy and a newer one can both be in the folder. Only one is
          current.
        </Card>
      </div>
    ),
  },
  {
    kicker: 'What we built',
    title:
      'An assistant that reads the documents, checks itself, and shows its work.',
    body: (
      <div className="slide-cards">
        <Card title="It reads">
          Fourteen policy PDFs (ten written for this project, four real public
          NIST documents) are split into small pieces and indexed, so the right
          passage can be found fast.
        </Card>
        <Card title="It decides what to do next">
          It can search again, read a whole page, or ask you a question when
          yours is unclear.
        </Card>
        <Card title="It proves it">
          Every quote in the answer is checked against the page it came from
          before you see it.
        </Card>
      </div>
    ),
  },
  {
    kicker: 'Walk through one question',
    title: '"What bandwidth limit applies to guests on the campus wifi?"',
    body: (
      <Steps
        items={[
          ['Understand', 'It breaks the question into what it needs to find.'],
          [
            'Search',
            'It looks through every document for the best matching passages.',
          ],
          [
            'Judge',
            'It asks itself: is this enough? If not, it searches again with different words.',
          ],
          [
            'Ask if unsure',
            'If the answer depends on something you did not say, it asks you.',
          ],
          [
            'Answer',
            'It writes a short answer and attaches the quote and page for each claim.',
          ],
          [
            'Check',
            'Each quote must appear word for word on that page, or the claim is removed.',
          ],
        ]}
      />
    ),
  },
  {
    kicker: 'You can watch it work',
    title: 'Every search and decision is listed as it happens.',
    body: (
      <div className="slide-cards">
        <Card title="Nothing hidden">
          The side panel shows each search, what came back, and why it searched
          again.
        </Card>
        <Card title="Click a citation">
          Opens the real page so you can read the passage in context.
        </Card>
        <Card title="Limits you can see">
          If it runs out of time or steps, it says so and gives what it found,
          instead of freezing.
        </Card>
      </div>
    ),
  },
  {
    kicker: 'Why you can trust it',
    title: 'It would rather say "I did not find it" than guess.',
    body: (
      <div className="slide-cards">
        <Card title="Quotes must be real">
          If a quote is not on the page it points to, that claim is thrown away.
        </Card>
        <Card title="Honest about gaps">
          When the documents do not cover a question, the answer says exactly
          that.
        </Card>
        <Card title="Documents cannot give orders">
          Text inside a document that says "ignore your rules" is treated as
          plain text, never as a command.
        </Card>
      </div>
    ),
  },
  {
    kicker: 'What is under the hood',
    title: 'Five parts, each with one job.',
    body: (
      <>
        <ol className="slide-parts">
          {[
            ['What you see', 'The web page', ['react']],
            [
              'The front door',
              'Delivers the page, adds HTTPS',
              ['nginx', 'caddy'],
            ],
            [
              'The application',
              'Handles requests, passcode, limits',
              ['fastapi'],
            ],
            ['The assistant', 'Plans, searches, checks', ['python']],
            [
              'Memory and AI',
              'Documents, speed-ups, the language model',
              ['postgresql', 'redis', 'openrouter'],
            ],
          ].map(([name, detail, logos], index) => (
            <li key={String(name)}>
              <span>{index + 1}</span>
              <strong>{name as string}</strong>
              <em>{detail as string}</em>
              <div>
                {(logos as string[]).map((logo) => (
                  <img key={logo} src={`/logos/${logo}.svg`} alt={logo} />
                ))}
              </div>
            </li>
          ))}
        </ol>
      </>
    ),
  },
  {
    kicker: 'How we know it works',
    title: `We asked 11 test questions. The assistant fully passed ${agentPassed}; the simple version passed ${simplePassed} of ${simpleCases.length}.`,
    body: (
      <>
        <ul className="slide-results" aria-label="Results by test question">
          {evaluationCases.map((c) => (
            <li key={c.id}>
              <span>{c.label}</span>
              <b className={`res-${c.agent === 'pass' ? 'pass' : 'fail'}`}>
                {c.agent === 'pass' ? 'passed' : 'missed'}
              </b>
              <b
                className={`res-${c.baseline === 'pass' ? 'pass' : c.baseline === 'n/a' ? 'na' : 'fail'}`}
              >
                {c.baseline === 'pass'
                  ? 'passed'
                  : c.baseline === 'n/a'
                    ? 'not tested'
                    : 'missed'}
              </b>
            </li>
          ))}
        </ul>
        <p className="slide-note">
          Columns: the assistant, then the simple version that searches once and
          answers once. The assistant tuned to these same questions, so a fresh
          set would be the honest next test.
        </p>
      </>
    ),
  },
  {
    kicker: 'What we learned by measuring',
    title: 'We tested each choice instead of trusting guesses.',
    body: (
      <div className="slide-cards">
        <Card title="Smaller pieces work better">
          Splitting documents into 200-word pieces found the right page more
          often than larger pieces.
        </Card>
        <Card title="Two kinds of search beat one">
          Matching by meaning and by exact words together beat either alone.
        </Card>
        <Card title="Some ideas did not help">
          An extra re-ranking step and a bigger model made no difference here,
          so we left them out.
        </Card>
      </div>
    ),
  },
  {
    kicker: 'What is next',
    title: 'Ready to share, and honest about what is left.',
    body: (
      <div className="slide-cards">
        <Card title="Safe to share">
          A passcode, request limits, a daily spending cap, and each visitor
          sees only their own work.
        </Card>
        <Card title="Not solved yet">
          Spotting that a newer policy replaced an old one, and asking the right
          clarifying question every time.
        </Card>
        <Card title="If it grew">
          Background processing for large uploads, cloud file storage, company
          sign-in and monitoring.
        </Card>
      </div>
    ),
  },
]

export function PresentationPage({ onBack }: { onBack: () => void }) {
  const [index, setIndex] = useState(0)
  const [full, setFull] = useState(false)
  const deck = useRef<HTMLElement>(null)

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

  const slide = slides[index]
  const pad = (n: number) => String(n).padStart(2, '0')
  return (
    <main className={`deck${full ? ' deck-full' : ''}`} ref={deck}>
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
        aria-live="polite"
        aria-label={`Slide ${index + 1} of ${slides.length}`}
      >
        <p className="eyebrow">{slide.kicker}</p>
        <h1>{slide.title}</h1>
        {slide.body}
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
