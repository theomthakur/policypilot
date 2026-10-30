import { useCallback, useEffect, useState } from 'react'
import { evaluationCases, evaluationRun } from '../data/evaluation'
import './Pages.css'

const TOTAL_TESTS = 71

interface Slide {
  kicker: string
  title: string
  body: React.ReactNode
}

function Stat({ value, label }: { value: string; label: string }) {
  return (
    <div className="slide-stat">
      <strong>{value}</strong>
      <span>{label}</span>
    </div>
  )
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

const flow = [
  'Plan',
  'Search',
  'Judge the evidence',
  'Search again or ask',
  'Answer',
  'Verify',
]
const agentPassed = evaluationCases.filter((c) => c.agent === 'pass').length
const baselineRun = evaluationCases.filter((c) => c.baseline !== 'n/a')
const baselinePassed = baselineRun.filter((c) => c.baseline === 'pass').length

const slides: Slide[] = [
  {
    kicker: 'NYU IT · AI Engineer take-home',
    title: 'Policy answers you can check.',
    body: (
      <>
        <p className="slide-lead">
          PolicyPilot answers questions about policy PDFs. It plans, searches,
          searches again when the evidence is thin, asks when a question is
          ambiguous, and shows only citations it has verified against the page.
        </p>
        <div className="slide-stats">
          <Stat value="10" label="policy PDFs" />
          <Stat value="4" label="read-only tools" />
          <Stat value={String(TOTAL_TESTS)} label="backend tests" />
          <Stat value="0" label="actions taken" />
        </div>
      </>
    ),
  },
  {
    kicker: '01 · Problem',
    title: 'A wrong answer with a real citation still looks right.',
    body: (
      <div className="slide-cards">
        <Card title="It drifts from the source">
          A fluent summary can be close to the policy and still wrong on the one
          number that matters.
        </Card>
        <Card title="It depends on who asks">
          Retention, renewal and access rules differ by role or data level. One
          answer for everyone is a guess.
        </Card>
        <Card title="Policies are replaced">
          A 2023 rule and a 2025 standard can disagree. Both are in the folder;
          only one is current.
        </Card>
      </div>
    ),
  },
  {
    kicker: '02 · How it works',
    title: 'The model decides the next step. Code decides the limits.',
    body: (
      <>
        <ol className="slide-flow">
          {flow.map((step, index) => (
            <li key={step}>
              <span>{index + 1}</span>
              {step}
            </li>
          ))}
        </ol>
        <p className="slide-note">
          Eight steps, six tool calls, 60 seconds and 25,000 tokens at most. A
          repeated call is blocked, a timeout is retried once, and hitting a
          limit returns a partial answer instead of hanging.
        </p>
      </>
    ),
  },
  {
    kicker: '03 · System design',
    title: 'Five layers, one source of truth.',
    body: (
      <>
        <div className="slide-stack">
          {[
            ['Browser', 'React, live trace over SSE'],
            ['Edge', 'Caddy and nginx'],
            ['API', 'FastAPI, passcode, session ownership'],
            ['Agent', 'State machine, tools, verifier'],
            ['Data', 'Postgres + pgvector, Redis, OpenRouter'],
          ].map(([name, detail], index) => (
            <div key={name}>
              <span>{index + 1}</span>
              <strong>{name}</strong>
              <em>{detail}</em>
            </div>
          ))}
        </div>
        <div className="slide-logos" aria-label="Technologies used">
          {[
            'react',
            'nginx',
            'fastapi',
            'postgresql',
            'redis',
            'openrouter',
            'docker',
          ].map((logo) => (
            <img key={logo} src={`/logos/${logo}.svg`} alt={logo} height="30" />
          ))}
        </div>
      </>
    ),
  },
  {
    kicker: '04 · Trust',
    title: 'A citation is shown only if its quote is on the page.',
    body: (
      <div className="slide-cards">
        <Card title="1 · Provenance">
          The evidence ID must come from a tool call in this turn.
        </Card>
        <Card title="2 · Location">
          The quote must be literal text on the cited document page.
        </Card>
        <Card title="3 · Or it is dropped">
          One repair attempt. Unsupported claims are removed, and the answer
          says what is missing.
        </Card>
      </div>
    ),
  },
  {
    kicker: '05 · Evidence',
    title: `The agent passed ${agentPassed} of ${evaluationCases.length} cases; the one-pass baseline ${baselinePassed} of ${baselineRun.length}.`,
    body: (
      <>
        <ul className="slide-results" aria-label="Evaluation results by case">
          {evaluationCases.map((c) => (
            <li key={c.id}>
              <span>{c.label}</span>
              <b className={`res-${c.agent === 'pass' ? 'pass' : 'fail'}`}>
                {c.agent}
              </b>
              <b
                className={`res-${c.baseline === 'pass' ? 'pass' : c.baseline === 'n/a' ? 'na' : 'fail'}`}
              >
                {c.baseline}
              </b>
            </li>
          ))}
        </ul>
        <p className="slide-note">
          Columns: agent, baseline. Deterministic checks on openai/gpt-4o-mini,{' '}
          {evaluationRun}. The four agent failures are listed openly; a manual
          page review is still to be done.
        </p>
      </>
    ),
  },
  {
    kicker: '06 · Engineering',
    title: 'Every retrieval choice was measured, not assumed.',
    body: (
      <>
        <div className="slide-stats">
          <Stat value="0.80 → 0.87" label="recall, top 3 pages" />
          <Stat value="0.87 → 0.93" label="recall, top 5 pages" />
          <Stat value="0.76 → 0.88" label="first-hit rank (MRR)" />
        </div>
        <p className="slide-note">
          200-token chunks beat 350 and 500. Hybrid search beat vector-only. A
          cross-encoder reranker and a larger embedding model did not help, so
          neither shipped. Gold pages come from the evaluation cases.
        </p>
      </>
    ),
  },
  {
    kicker: '07 · Next',
    title: 'Built to be deployed, honest about what is left.',
    body: (
      <div className="slide-cards">
        <Card title="Protected">
          Passcode, rate limit, daily budget cap, and one session can never read
          another.
        </Card>
        <Card title="Still open">
          Older-vs-newer policy detection, ambiguity questions and weak-search
          detection are not reliable yet.
        </Card>
        <Card title="At scale">
          Queue workers, object storage, a reranker only if it wins, SSO and
          tracing.
        </Card>
      </div>
    ),
  },
]

export function PresentationPage({ onBack }: { onBack: () => void }) {
  const [index, setIndex] = useState(0)
  const go = useCallback(
    (delta: number) =>
      setIndex((current) =>
        Math.min(slides.length - 1, Math.max(0, current + delta)),
      ),
    [],
  )

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'ArrowRight' || event.key === ' ') {
        event.preventDefault()
        go(1)
      } else if (event.key === 'ArrowLeft') {
        go(-1)
      } else if (event.key.toLowerCase() === 'f') {
        if (document.fullscreenElement) void document.exitFullscreen()
        else void document.documentElement.requestFullscreen?.()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [go])

  const slide = slides[index]
  const pad = (n: number) => String(n).padStart(2, '0')
  return (
    <main className="page deck">
      <div className="deck-bar">
        <button className="page-back" type="button" onClick={onBack}>
          <span aria-hidden="true">←</span> Back to workspace
        </button>
        <span className="deck-hint">
          ← → or Space to move · F for fullscreen
        </span>
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
