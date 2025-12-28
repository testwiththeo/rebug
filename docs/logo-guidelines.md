# Rebug Logo & Brand Guidelines

Inspired by Apple's design philosophy: simplicity, precision, and consistency.

---

## 1. Logo

### 1.1 Primary Logomark

The Rebug logomark is an abstract geometric bug form constructed from three interlocking rounded shapes forming an infinite-loop triangle — symbolizing replay, cycles, and catching issues before they escape.

Construction:
- Three circular segments, each with a 45° cutout at the vertex
- Arranged in an equilateral triangle pointing upward
- Each segment shares the same corner radius (cap radius = stroke width × 0.5)
- The negative space at center forms a hexagon
- Overall bounding box: square proportion (1:1)

### 1.2 Clear Space

Minimum clear space = height of the logomark × 0.5 on all sides.

No text, graphics, or UI elements may intrude into this zone.

### 1.3 Minimum Size

| Medium | Minimum Width |
|--------|---------------|
| Digital (screen) | 28 px |
| Print | 0.5 in (12.7 mm) |
| Favicon | 16 px (use simplified variant) |

Below these sizes, use the simplified favicon variant (single geometric dot + arc).

### 1.4 Wordmark

The wordmark is set in **SF Pro Display Medium** with tight tracking (−20 em).

```
R E B U G
```

- All uppercase
- Letter spacing: −20 em
- Cap height matches logomark bounding box height
- The "R" and "g" extend slightly above and below baseline respectively, matching Apple's vertical metrics

Combination lockup: logomark to the left of wordmark, separated by exactly 0.25× logomark width.

Stacked lockup (for small spaces): logomark centered above wordmark, separated by 0.125× logomark height.

---

## 2. Color Palette

### 2.1 Primary Colors

| Role | Hex | RGBA | Pantone | Usage |
|------|-----|------|---------|-------|
| Rebug Red (Primary) | `#FF3B30` | `255, 59, 48, 1` | 1788 C | Logomark, primary buttons, active states |
| Rebug Black | `#1D1D1F` | `29, 29, 31, 1` | Black 6 C | Wordmark, primary text |
| Rebug White | `#FFFFFF` | `255, 255, 255, 1` | — | Light mode background, inverse logomark |

### 2.2 Secondary Colors

| Role | Hex | Usage |
|------|-----|-------|
| Debug Blue | `#007AFF` | Links, replay player accent |
| Crash Amber | `#FF9500` | Warnings, severity indicators |
| Pass Green | `#34C759` | Success states, confirmed fixes |

### 2.3 Neutral Palette

| Role | Hex | Usage |
|------|-----|-------|
| Text Primary | `#1D1D1F` | Body text |
| Text Secondary | `#86868B` | Labels, captions |
| Fill Primary | `#F5F5F7` | Card backgrounds |
| Fill Secondary | `#E8E8ED` | Borders, dividers |
| Fill Tertiary | `#D2D2D7` | Disabled states |

### 2.4 Dark Mode

| Role | Hex |
|------|-----|
| Background | `#1C1C1E` |
| Surface | `#2C2C2E` |
| Text Primary | `#F5F5F7` |
| Text Secondary | `#98989D` |
| Logomark | `#FF453A` (slightly desaturated for dark) |

---

## 3. Typography

### 3.1 Primary Font: SF Pro

Apple's system font. For digital properties, use system font stack:

```css
font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Helvetica Neue', sans-serif;
```

| Usage | Font | Weight | Size | Leading |
|-------|------|--------|------|---------|
| Wordmark | SF Pro Display | Medium | Custom | Cap height |
| Heading 1 | SF Pro Display | Bold | 48 / 40 / 32 | 1.1 |
| Heading 2 | SF Pro Display | Semibold | 28 / 24 / 20 | 1.15 |
| Heading 3 | SF Pro Text | Semibold | 20 / 18 / 16 | 1.2 |
| Body | SF Pro Text | Regular | 16 / 15 / 14 | 1.4 |
| Caption | SF Pro Text | Regular | 13 / 12 | 1.3 |
| Label (UI) | SF Pro Text | Medium | 13 / 12 | 1.2 |

### 3.2 Monospace: SF Mono

```css
font-family: 'SF Mono', 'Menlo', 'Consolas', monospace;
```

| Usage | Weight | Size |
|-------|--------|------|
| Console log display | Regular | 13 |
| Code snippets | Regular | 14 |
| File paths | Regular | 12 |

---

## 4. Logo Variants

### 4.1 Full Color (Default)

Rebug Red logomark + Rebug Black wordmark on white/light background.

### 4.2 Monochrome Black

Solid black logomark + wordmark. For single-color print, fax, grayscale.

### 4.3 Monochrome White

Solid white logomark + wordmark on Rebug Black or dark photography backgrounds.

### 4.4 Favicon / App Icon

Simplified variant: single rounded square containing the central hexagon negative space. No text.

- iOS: 1024×1024 pt (export at 1024×1024 px)
- Chrome Web Store: 128×128 px, 48×48 px
- macOS: 512×512 pt

App icon uses a squircle mask matching Apple's `LafIcon` geometry:
- Corner radius = 22.5% of icon width
- No drop shadow on the icon itself (let the OS render it)

---

## 5. Logo Usage Rules

### 5.1 Don'ts

- Do not recolor the logomark — use only approved brand colors
- Do not rotate the logomark
- Do not add drop shadows, glows, or embossing
- Do not outline or stroke the logomark shapes
- Do not place the logomark on busy photographic backgrounds without the white/black container
- Do not squash or stretch proportions
- Do not rearrange the three segments
- Do not pair the logomark with any font other than SF Pro
- Do not animate the logomark in a way that breaks the triangular relationship

### 5.2 Background Containers

When placing the logomark on photography or gradients, use a circular container:
- Diameter = logomark width + clear space × 2
- Fill: white on dark photos, black at 60% opacity on light photos
- Corner radius: 50% (perfect circle)

---

## 6. Brand Voice & Design Principles

### 6.1 Tone

- Precise, not academic
- Confident, not arrogant
- Technical, not jargon-heavy
- Human, not corporate

### 6.2 Design Tenets (Apple-aligned)

1. **Deference.** The interface defers to the content. The brand defers to the product's utility.
2. **Clarity.** Every element exists for a reason. If it doesn't serve the user, remove it.
3. **Depth.** Realistic and meaningful layers. The replay viewer should feel like looking through a window, not at a document.

### 6.3 Spacing System

Base unit: 8 px. All spacing, padding, and margins derive from multiples of 8.

| Token | px | Usage |
|-------|----|-------|
| `space-1` | 4 | Micro spacing, icon padding |
| `space-2` | 8 | Button padding, row gaps |
| `space-3` | 12 | Card padding small |
| `space-4` | 16 | Card padding, section gaps |
| `space-6` | 24 | Section margins |
| `space-8` | 32 | Page margins |
| `space-12` | 48 | Major section breaks |
| `space-16` | 64 | Hero sections |

### 6.4 Border Radius

| Token | px | Usage |
|-------|----|-------|
| `radius-sm` | 6 | Buttons, inputs |
| `radius-md` | 10 | Cards, modals |
| `radius-lg` | 14 | Sheets, pickers |
| `radius-xl` | 20 | Full-screen cards |

Do not exceed 20 px for any interactive element. Never use fully pill-shaped buttons (unlike Apple's own buttons in iOS).

---

## 7. Application Examples

### 7.1 Website Header

```
[Logomark]  REBUG    [Product] [Pricing] [Docs] [Download]
```

- Logomark: 32×32 px, Rebug Red
- Wordmark: SF Pro Display Medium, Rebug Black, 22 px
- Navigation: SF Pro Text Regular, 14 px

### 7.2 Extension Popup

- Icon: favicon variant at 24×24 px
- Header: Rebug Red bar at 3 px top border
- Background: Fill Primary (`#F5F5F7`)
- Record button: Rebug Red with white SF Pro Text Medium 14 px

### 7.3 Social Sharing Card

- Background: gradient from `#FF3B30` (top) to `#1D1D1F` (bottom)
- Logomark: Monochrome White, centered
- Tagline: SF Pro Display Regular, white, 24 px, placed below
- Minimum dimensions: 1200×628 px (Open Graph)

### 7.4 Business Card

- Front: Full-color logomark + wordmark centered
- Back: Name, title, email in SF Pro Text Regular 9 pt
- Paper: uncoated matte, 300 gsm
- Colors: spot PMS 1788 C + black

---

## 8. File Deliverables

| File | Format | Contents |
|------|--------|----------|
| rebug-logo-primary.svg | SVG | Full-color logomark + wordmark (horizontal) |
| rebug-logo-stacked.svg | SVG | Full-color logomark + wordmark (stacked) |
| rebug-logo-black.svg | SVG | Monochrome black logomark |
| rebug-logo-white.svg | SVG | Monochrome white logomark |
| rebug-icon-1024.png | PNG | App icon at 1024×1024 px |
| rebug-favicon.svg | SVG | Simplified favicon variant |
| rebug-wordmark.svg | SVG | Wordmark only (for header use) |

All SVGs use `viewBox` with no fixed `width`/`height` to allow scaling. Export PNGs at 2× and 3× for Retina.

---

## 9. Accessibility

- Minimum contrast ratio: 4.5:1 for all text (WCAG AA)
- Rebug Red on white: contrast ratio 5.2:1 (passes AA for all text)
- Rebug Red on black: contrast ratio 5.8:1 (passes AA)
- Do not use color alone to convey meaning — pair with icons or text labels
- Interactive elements have a minimum touch target of 44×44 pt
