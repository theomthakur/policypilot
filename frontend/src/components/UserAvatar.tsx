import { viewerFirstName } from './viewerIdentity'

/** A compact personal marker for the signed-in person. */
export function UserAvatar({ name }: { name: string | null }) {
  return <span>{viewerFirstName(name).charAt(0).toUpperCase()}</span>
}
