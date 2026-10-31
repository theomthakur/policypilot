// Drive a running PolicyPilot through the browser: sign in with the identity provider, optionally upload a PDF and
// ask a question, then print what the signed-in user can see. Usage:
//   node flow.mjs --base http://localhost:8088 --user alice --password-file ../../.k8s-demo-credentials \
//        [--upload file.pdf] [--ask "question"] [--shot out.png] [--expect-doc name] [--expect-no-doc name]
import { chromium } from 'playwright'
import { readFileSync } from 'node:fs'

const args = Object.fromEntries(
  process.argv.slice(2).reduce((acc, value, index, all) => {
    if (value.startsWith('--')) acc.push([value.slice(2), all[index + 1]?.startsWith('--') ? 'true' : all[index + 1]])
    return acc
  }, []),
)
const base = args.base ?? 'http://localhost:8080'
const password =
  args.password ??
  readFileSync(args['password-file'], 'utf8')
    .split('\n')
    .map((line) => line.split('='))
    .find(([name]) => name === args.user)?.[1]
if (!password) throw new Error('no password for ' + args.user)

const browser = await chromium.launch()
const page = await (await browser.newContext({ viewport: { width: 1440, height: 860 } })).newPage()
const log = (message) => console.log(`[${args.user}] ${message}`)

await page.goto(base)
await page.getByRole('link', { name: 'Sign in' }).waitFor({ timeout: 30000 })
log('sign-in screen shown to a signed-out visitor')
await page.getByRole('link', { name: 'Sign in' }).click()
await page.locator('#username').fill(args.user)
await page.locator('#password').fill(password)
await page.locator('#kc-login').click()
await page.locator('.tool-avatar').waitFor({ timeout: 60000 }).catch(async (error) => {
  await page.screenshot({ path: '/tmp/flow-failure.png' })
  console.error('stuck at', page.url())
  throw error
})
log('signed in through the identity provider')

if (args.upload) {
  const before = await page.locator('.document-card').count()
  await page.locator('input[type=file]').setInputFiles(args.upload)
  await page.waitForFunction(
    (n) => document.querySelectorAll('.document-card').length > n,
    before,
    { timeout: 30000 },
  )
  await page.waitForFunction(
    () => ![...document.querySelectorAll('.document-status')].some((el) => /queued|processing/i.test(el.textContent)),
    null,
    { timeout: 90000 },
  )
  log(`uploaded ${args.upload.split('/').pop()} and it finished processing`)
}
if (args.ask) {
  await page.locator('#question').fill(args.ask)
  await page.locator('#question').press('Enter')
  await page.locator('.answer-bubble:not(.working-line)').first().waitFor({ timeout: 180000 })
  const text = await page.locator('.answer-bubble:not(.working-line)').last().innerText()
  log('answer: ' + text.replace(/\s+/g, ' ').slice(0, 220))
  log('citations: ' + (await page.locator('.citation-chip').count()))
}
await page.waitForTimeout(2500) // let the document list refresh after the conversation attaches
const names = await page.locator('.document-details strong').allInnerTexts()
log(`documents visible: ${names.length}; not from the shared corpus: ${names.filter((n) => !/^(NIST|Acceptable|Data|Generative|Password|Identity|Cybersecurity|Remote|Account|Research|Approved)/.test(n)).join(', ') || 'none'}`)
if (args['expect-doc']) {
  if (!names.some((n) => n.includes(args['expect-doc']))) throw new Error('expected document missing: ' + args['expect-doc'])
  log('can see ' + args['expect-doc'])
}
if (args['expect-no-doc']) {
  if (names.some((n) => n.includes(args['expect-no-doc']))) throw new Error('isolation broken: ' + args['expect-no-doc'])
  log('cannot see ' + args['expect-no-doc'] + ' (isolated)')
}
if (args.shot) await page.screenshot({ path: args.shot })
await browser.close()
