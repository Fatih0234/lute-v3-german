# Analysis: Why "Es hatte ein Mann einen Esel" validation fails

## Problem Summary

The validation check `sentenceContext.indexOf(termText) >= 0` returns `-1` (false negative) even when the term text is visually present at the beginning of the sentence context.

## Root Cause

**The term text and context are extracted from DIFFERENT sources with DIFFERENT zero-width space (ZWS) handling:**

### 1. How Term Text is Built (for multiword terms)

**File:** `/Volumes/T7/projects/lute-v3-light-only-german/lute/static/js/lute.js` (lines 278-279)

```javascript
function show_multiword_term_edit_form(selected) {
  const textparts = selected.toArray().map((el) => $(el).text());  // <-- Uses .text() - NO ZWS
  const text = textparts.join('').trim();
  // ...
}
```

- Uses jQuery `.text()` which gets the **rendered visible text**
- The rendered text has **ZERO-WIDTH SPACES REMOVED** by the backend

**Backend (text_item.py line 95):**
```python
@property
def html_display_text(self):
    return self.display_text.replace(zws, "")  # <-- ZWS stripped for display
```

**Template (textitem.html line 7):**
```html
<span data-text="{{ item.text }}">{{ item.html_display_text | safe }}</span>
```
- `data-text` = raw text WITH ZWS
- Visible content (`html_display_text`) = text WITHOUT ZWS

So `.text()` gets text **WITHOUT ZWS**.

---

### 2. How Context is Built

**File:** `/Volumes/T7/projects/lute-v3-light-only-german/lute/static/js/lute.js` (lines 209-236)

```javascript
function _get_sentence_context(el) {
  // ...
  const sentenceText = sentenceElements.map(function() {
    const text = $(this).attr('data-text') || $(this).text();  // <-- Uses data-text WITH ZWS
    return text.replace(new RegExp(zws, 'g'), '');  // <-- Tries to remove ZWS
  }).get().join('');
  // ...
}
```

The context builder **TRIES** to remove ZWS, but there's a subtle issue:

1. It prioritizes `data-text` attribute (line 229)
2. `data-text` contains raw text WITH zero-width spaces
3. The ZWS removal happens AFTER getting the attribute

---

### 3. Where the Mismatch Happens

**The validation check in _form.html (line 385):**
```javascript
const isInContext = sentenceContext.indexOf(termText) >= 0;
```

**Scenario with German text "Es hatte ein Mann einen Esel":**

| Source | Content | ZWS State |
|--------|---------|-----------|
| `termText` (from `.text()`) | `"Es hatte ein Mann einen Esel"` | **NO ZWS** |
| `sentenceContext` (from `data-text`) | `"\u200BEs\u200Bhatte\u200Bein\u200BMann\u200Beinen\u200BEsel\u200B"` | **HAS ZWS** |

The validation does:
```javascript
"\u200BEs\u200Bhatte...".indexOf("Es hatte...")  // Returns -1 (NOT FOUND)
```

**The ZWS characters break the string matching!**

---

### 4. Why `_get_sentence_context` ZWS Removal May Fail

Looking at line 227-230 in lute.js:
```javascript
const zws = "\u200B";
const sentenceText = sentenceElements.map(function() {
  const text = $(this).attr('data-text') || $(this).text();
  return text.replace(new RegExp(zws, 'g'), '');
}).get().join('');
```

**Potential issues:**

1. **Regex escaping**: If `zws` contains special regex characters (it doesn't, but could be encoding issues)

2. **Unicode normalization**: If the data-text contains different Unicode representations of the same character

3. **Additional hidden characters**: The text might contain:
   - Soft hyphens (`\u00AD` - `&shy;`)
   - Other zero-width characters
   - Word joiners

4. **Double-encoded entities**: The data-text might have HTML entities that aren't decoded

---

### 5. Evidence from the Debug Console

From the user's debug output showing the validation failure, the term text clearly appears at the start of the context, yet `indexOf` returns -1. This strongly suggests hidden characters present in one string but not the other.

---

## The Fix

**Option 1: Normalize both strings before comparison (Recommended)**

In `/Volumes/T7/projects/lute-v3-light-only-german/lute/templates/term/_form.html`, normalize both strings:

```javascript
// Normalize function to remove all zero-width and invisible characters
function normalizeText(text) {
  if (!text) return '';
  return text
    .replace(/\u200B/g, '')      // Zero-width space
    .replace(/\u200C/g, '')      // Zero-width non-joiner
    .replace(/\u200D/g, '')      // Zero-width joiner
    .replace(/\u00AD/g, '')      // Soft hyphen
    .replace(/\uFEFF/g, '')      // Zero-width no-break space (BOM)
    .trim();
}

// In validation:
const normalizedContext = normalizeText(sentenceContext);
const normalizedTerm = normalizeText(termText);
const isInContext = normalizedContext.indexOf(normalizedTerm) >= 0;
```

**Option 2: Fix `_get_sentence_context` to use `.text()` instead of `data-text`**

Change line 229 in lute.js:
```javascript
// OLD:
const text = $(this).attr('data-text') || $(this).text();

// NEW:
const text = $(this).text();  // Always use visible text, no ZWS
```

This ensures both term and context come from the same source.

**Option 3: Use string normalization for the translation API call**

In `/Volumes/T7/projects/lute-v3-light-only-german/lute/translation/service.py`, the code already does some normalization (lines 62-65):

```python
zws = "\u200B"
selected_normalized = selected_text.replace(zws, "").replace("  ", " ").strip()
context_normalized = context_text.replace(zws, "").replace("  ", " ").strip()
```

This same normalization should be applied in the JavaScript validation.

---

## Summary Table

| Function | Source | ZWS Handling | Result |
|----------|--------|--------------|--------|
| `show_multiword_term_edit_form` | `.text()` | No ZWS (already stripped by backend) | Clean text |
| `_get_sentence_context` | `data-text` attr | Removes ZWS manually | Should be clean, but may have edge cases |
| Validation comparison | Both above | Direct comparison | **FAILS** due to hidden chars |

**Bottom line:** The validation fails because the context string contains hidden characters (zero-width spaces) that the term string does not have, causing `indexOf` to return -1 even when the text visually matches.
