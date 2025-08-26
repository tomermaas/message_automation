# Kidum Message-Review Style Guide

This guide defines the visual language for the Kidum message-review web app. All screens are Hebrew-first and right-to-left oriented.

## Colors
| Role | Color | Hex |
| --- | --- | --- |
| Primary Accent | ![#5F2EEA](https://via.placeholder.com/15/5F2EEA/5F2EEA.png) | `#5F2EEA` |
| Secondary Accent | ![#FF5555](https://via.placeholder.com/15/FF5555/FF5555.png) | `#FF5555` |
| Background | ![#F5F5F5](https://via.placeholder.com/15/F5F5F5/F5F5F5.png) | `#F5F5F5` |
| Card | ![#FFFFFF](https://via.placeholder.com/15/FFFFFF/FFFFFF.png) | `#FFFFFF` |
| Text | ![#333333](https://via.placeholder.com/15/333333/333333.png) | `#333333` |
| Success | ![#2D8C3C](https://via.placeholder.com/15/2D8C3C/2D8C3C.png) | `#2D8C3C` |
| Error | ![#D32F2F](https://via.placeholder.com/15/D32F2F/D32F2F.png) | `#D32F2F` |

## Typography
- **Primary Font:** Heebo, sans-serif
- **Headline:** 24px, bold
- **Subheadline:** 18px, medium
- **Body:** 16px, regular
- **Caption:** 14px, regular

## Components
### Login Form
- Centered card with username, password, avatar (optional), and "Forgot Password" link.
- Primary button: "כניסה" using purple accent and 8px radius.

### Filter Bar
- Includes course selector, message-type dropdown, search input, and "רענון" button.
- Immediate feedback via toast or inline status text.

### Message Card
- Shows student name, timestamps, exam score, target score, gap, gap change, status badge, and message preview.
- Cards lift on hover and highlight on focus.
- Gap values color-coded: success for positive changes, error for negative.

### Pagination / Scroll
- Infinite scroll with loading spinner, preserving filter state.

### Editor Modal
- TipTap-based editor with bold, italic, underline, text color, font size, emoji picker, undo/redo.
- Defaults to RTL alignment with 16px padding and 1px border.
- Buttons: "שמור", "שמור וסגור", "בטל".

## Spacing
- Base unit: 8px.
- Card padding: 16px.
- Grid gap: 24px (desktop), 16px (tablet), 8px (mobile).

## Interaction States
- Hover: subtle lift and shadow (`transition: 150ms`).
- Focus: 2px solid purple outline for keyboard navigation.
- Disabled: 40% opacity with no lift.
- Error: red text and border with ARIA `aria-invalid="true"`.

## Accessibility
- All controls provide visible focus states.
- ARIA roles for interactive elements.
- Supports RTL keyboard navigation.
