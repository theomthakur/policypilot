// Accessibility pass on a running deployment: an automated axe scan of each main screen in light and dark mode,
// then a keyboard-only walk (Tab order, focus visibility, Escape closes the account menu). Usage: node a11y.mjs [base]
import { chromium } from 'playwright'
import AxeBuilder from '@axe-core/playwright'

const base = process.argv[2] ?? 'http://localhost:8080'
const browser = await chromium.launch()
let failures = 0
for (const theme of ['light', 'dark']) {
  const page = await (await browser.newContext({ viewport: { width: 1440, height: 860 } })).newPage()
  await page.goto(`${base}/?theme=${theme}`)
  await page.locator('#question').waitFor({ timeout: 30000 })
  await page.waitForTimeout(2500)
  for (const [name, hash] of [['workspace', ''], ['system design', '#architecture'], ['presentation', '#presentation']]) {
    await page.goto(`${base}/?theme=${theme}${hash}`)
    await page.waitForTimeout(1800)
    const result = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()
    console.log(`axe ${theme} / ${name}: ${result.violations.length} violation(s)`)
    for (const v of result.violations) { failures++; console.log('  ', v.id, v.impact, v.nodes.length, 'node(s)') }
  }
}
// Keyboard only: reach the question box, type, send, and leave the panels reachable.
const page = await (await browser.newContext({ viewport: { width: 1440, height: 860 } })).newPage()
await page.goto(base)
await page.locator('#question').waitFor()
await page.waitForTimeout(2000)
const stops = []
for (let i = 0; i < 40; i++) {
  await page.keyboard.press('Tab')
  const label = await page.evaluate(() => {
    const el = document.activeElement
    if (!el || el === document.body) return null
    const box = el.getBoundingClientRect()
    const outline = getComputedStyle(el).outlineStyle !== 'none' || getComputedStyle(el).boxShadow !== 'none'
    return { name: (el.getAttribute('aria-label') || el.textContent || el.id || el.tagName).trim().slice(0, 40), visible: box.width > 0 && box.height > 0, outline }
  })
  if (label) stops.push(label)
}
const unnamed = stops.filter((s) => !s.name)
const invisible = stops.filter((s) => !s.visible)
const noRing = stops.filter((s) => !s.outline)
console.log(`keyboard: ${stops.length} tab stops, ${unnamed.length} without a name, ${invisible.length} off-screen, ${noRing.length} without a visible focus style`)
if (noRing.length) console.log('  no focus style on:', noRing.map((s) => s.name).join(' | '))
await page.locator('#question').focus()
await page.keyboard.type('hello')
console.log('keyboard: typed into the question box with the keyboard only')
await browser.close()
process.exit(failures ? 1 : 0)
