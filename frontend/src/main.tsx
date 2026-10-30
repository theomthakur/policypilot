import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { App } from './App'
import './styles.css'
import './theme.css'

// Apply the saved or system theme before the first paint so there is no flash.
// ?theme=dark|light and ?developer=1|0 in the address set and remember a choice (handy for sharing a link).
try {
  const params = new URLSearchParams(window.location.search)
  const forcedTheme = params.get('theme')
  if (forcedTheme === 'dark' || forcedTheme === 'light')
    window.localStorage.setItem('pp_theme', forcedTheme)
  const forcedDeveloper = params.get('developer')
  if (forcedDeveloper === '1' || forcedDeveloper === '0')
    window.localStorage.setItem(
      'pp_developer',
      forcedDeveloper === '1' ? 'true' : 'false',
    )
  const saved = window.localStorage.getItem('pp_theme')
  document.documentElement.dataset.theme =
    saved === 'dark' || saved === 'light'
      ? saved
      : window.matchMedia('(prefers-color-scheme: dark)').matches
        ? 'dark'
        : 'light'
} catch {
  document.documentElement.dataset.theme = 'light'
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 10_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </StrictMode>,
)
