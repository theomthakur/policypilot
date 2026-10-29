interface PolicyPilotMarkProps {
  className?: string
}

export function PolicyPilotMark({ className = '' }: PolicyPilotMarkProps) {
  return (
    <img
      className={`policy-pilot-mark ${className}`.trim()}
      src="/policy-pilot-mark.png"
      alt=""
      aria-hidden="true"
    />
  )
}
