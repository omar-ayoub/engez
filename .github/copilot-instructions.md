# ENGEZ Design Context

## Users
Field workers on Egyptian construction sites, outdoor events, and freight
yards. They work in harsh conditions — bright sunlight, dust, gloves, poor
connectivity. They need to log expenses as fast as sending a WhatsApp voice
note. Their phone is their only tool. They are not tech-savvy and should
never feel confused or overwhelmed.

Secondary users are office accountants who review and approve expenses on
desktop or tablet. They need clear, scannable queues with quick approve/
reject actions.

Admins manage companies, users, and projects. They need simple CRUD screens.

## Brand Personality
Calm. Simple. Swift.

ENGEZ should feel like a trusted pocket notebook — always ready, never
in the way. The interface should make users feel relaxed, not anxious.
Every screen should have one obvious action. Silence is preferred over
noise — no unnecessary badges, counters, or status bars.

## Aesthetic Direction
Calm utility. Clean, spacious, generous whitespace. Soft dark surfaces
with subtle elevation. Large, confident typography. Minimal chrome.

**Primary reference: WhatsApp** — specifically its simplicity and speed.
WhatsApp succeeds in Egypt because it disappears into the task. No
onboarding walls, no feature tours, no settings rabbit holes. You open
it, you do the thing, you leave. ENGEZ should feel exactly like that
for expenses: open, capture, done. Borrow WhatsApp's patterns:
- Instant response to every tap (no loading spinners for local actions)
- Familiar bottom-anchored actions
- Minimal screen chrome — content fills the viewport
- Status communicated inline, not via modals or banners
- Zero learning curve for Egyptian users who already live in WhatsApp

Secondary references: Wise (TransferWise) for calm finance UI, Linear
for minimal dark interfaces.

## Design Principles

1. **One Screen, One Job** — Each screen does exactly one thing. No tabs,
   no accordions, no "see more" links. If it needs explanation, simplify it.

2. **Calm Over Clever** — No animations for the sake of delight. No
   micro-interactions that slow things down. Motion is used only to show
   spatial relationships (slide in/out) or confirm actions (checkmark).

3. **Silence is a Feature** — Empty states are peaceful, not sad. Success
   is quiet (a subtle checkmark), not celebratory (confetti). Errors are
   helpful, not alarming.

4. **Thumb-First** — Every interactive element is reachable by thumb in
   one-handed portrait mode. Primary actions live at the bottom of the
   screen, never behind a hamburger menu.

5. **Trust Through Transparency** — Show sync status honestly. Show
   amounts clearly. Never hide information that affects money. The user
   should always know: did my expense go through?

## Design Constraints
- RTL-first: all layouts must work in Arabic RTL
- Touch targets: minimum 44x44px (field workers wear gloves)
- High contrast: receipts viewed in outdoor sunlight
- Dark mode default: reduces battery on OLED field devices
- WCAG AA minimum for all text and interactive elements
- No color-only status indicators — use icons/labels alongside color

## Typography
- Primary: IBM Plex Arabic (Arabic text)
- Secondary: IBM Plex Sans (English text, numbers)
- Monospace: IBM Plex Mono (amounts, codes, invoice numbers)

## Color System
- Brand: Deep teal (#0D9488) — trust, calm, finance
- Brand light: Teal (#14B8A6) — hover states, active elements
- Accent: Amber (#F59E0B) — pending states, gentle warnings
- Success: Emerald (#10B981) — approved, synced, confirmed
- Danger: Rose (#F43F5E) — rejected, fraud flags, errors
- Surface: Neutral grays with low saturation — dark mode default

## Anti-References
- No purple gradients
- No card-in-card nesting
- No decorative illustrations on functional screens
- No Inter font (IBM Plex only)
- No dense data tables on mobile — use cards or lists
- No multi-step wizards when a single screen suffices
- No skeleton screens longer than 200ms
