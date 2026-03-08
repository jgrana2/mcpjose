---
name: wolfram-alpha
description: Query Wolfram Alpha for exact computations, symbolic mathematics, unit conversions, scientific data, and factual answers. Use this skill for mathematical calculations (algebra, calculus, equations), technical conversions, scientific constants, financial data, nutritional information, and any query requiring computational precision. Prefer this over general LLM responses when correctness matters more than prose, and especially for symbolic math, equation solving, and technical calculations.
---

# Wolfram Alpha Skill

## When to Use

Use the Wolfram Alpha tool (`mcpjose_wolfram_alpha`) for queries requiring:

- **Mathematical computations**: Algebra, calculus, statistics, equations
- **Symbolic manipulation**: Factoring, expanding, simplifying expressions
- **Unit conversions**: Currency, measurements, time zones (metric/nonmetric)
- **Scientific data**: Physics constants, chemical properties, astronomical data
- **Factual calculations**: Population statistics, financial data, demographics
- **Date and time**: Time zone conversions, date arithmetic, historical dates
- **Nutritional information**: Food composition, dietary calculations
- **Engineering**: Formulas, material properties, conversions

### When NOT to Use

- General web search (use `mcpjose_search` instead)
- Reading specific URLs or PDFs (use `mcpjose_navigate_to_url`)
- Simple questions answerable from general knowledge

## Tool Summary

- **Tool**: `mcpjose_wolfram_alpha`
- **Inputs**:
  - `query` (required): Natural-language or mathematical query
  - `maxchars` (optional): Cap response length when verbose
  - `units` (optional): `metric` or `nonmetric`
  - `assumption` (optional): Advanced disambiguation
- **Output**: `{ ok, provider, query, text?, status_code?, error? }`

## Query-Writing Workflow

1. Start with one concrete task per query
2. Use compact math syntax for algebra/calculus
3. Make the domain explicit when needed (`over the reals`, `for x`, `with respect to x`)
4. If the tool returns `ok: false` or a `501` error, retry with tighter Wolfram-style syntax
5. If the answer is too long, add `maxchars`

## Effective Phrasing Patterns

### Mathematical Syntax

**Algebra & Equations:**
- Factoring: `factor x^12 + x^6 + 1`
- Expanding: `expand (x+1)^10`
- Simplifying: `simplify (x^2-1)/(x-1)`
- Solving: `solve x^2 - 5 x + 6 = 0`
- Domain-restricted: `solve x^4 - 10 x^2 + 9 = 0 over the reals`
- Systems: `solve x+y=7, x y = 10`

**Calculus:**
- Derivatives: `d/dx (x^x)` or `derivative of x^2 * sin(x)`
- Integrals: `integrate x^2 sin x`
- Series: `series sin x about x=0 to order 8`

**Linear Algebra:**
- Matrix operations: `eigenvalues {{1,2},{3,4}}`
- Determinants: `det {{1,2},{3,4}}`

**Advanced:**
- Resultants: `resultant(x^4 + a x + b, 4 x^3 + a, x)`
- Discriminants: `discriminant(x^4 + a x + b, x)`

### Natural Language Queries

**Unit Conversions:**
- `convert 10 miles to km`
- `100 miles per hour in kilometers per hour`
- `5 feet 10 inches in centimeters`

**Scientific Data:**
- `speed of light in meters per second`
- `atomic mass of carbon`
- `distance from Earth to Mars`

**Finance:**
- `Apple Inc stock price`
- `Microsoft market cap`
- `convert 100 USD to Euros`

**Nutrition:**
- `nutrition facts for 100g almonds`
- `calories in a banana`

**Date/Time:**
- `time in Tokyo right now`
- `days until December 25, 2025`

## Rewrite Patterns for Success

When natural language fails, use these compact forms:

- ❌ `factor over the integers: x^12 + x^6 + 1`
- ✅ `factor x^12 + x^6 + 1`

- ❌ `resultant of f and g with respect to x`
- ✅ `resultant(f, g, x)`

- ❌ Long sentences with extra words
- ✅ Keep only the mathematical task and operands

- ❌ Multiple asks in one query
- ✅ Split into separate calls: `factor ...` then `solve ...`

## Worked Examples

These styles are known to work well:

```
solve over the reals: sqrt(x+sqrt(2x-1)) + sqrt(x-sqrt(2x-1)) = 3
factor x^12 + x^6 + 1
solve over the reals: x^2 + y^2 + z^2 = 14, x + y + z = 6, xyz = 6
resultant(x^4 + a x + b, 4 x^3 + a, x)
integrate e^x * sin(x)
d/dx (sin(x) * cos(x))
```

## Best Practices

1. **Be specific and natural** for general queries
2. **Use symbolic syntax** for complex math
3. **Include units** for measurement queries
4. **Specify context** for ambiguous terms (e.g., `Apple Inc` not just `Apple`)
5. **One task per query** - don't bundle multiple operations

## Parameter Usage

- **`maxchars`**: Use when results may include long derivations
- **`units`**: Use for measurement queries (`metric` or `nonmetric`)
- **`assumption`**: Only for advanced disambiguation; prefer encoding clarifications in `query`

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ok: false` with `501` | Rewrite query using shorter, more symbolic syntax |
| Ambiguous result | Add variable, domain, or operation explicitly |
| Verbose output | Retry with `maxchars` parameter |
| No interpretation | Reformulate with different phrasing or simplify the query |

## Integration with Other Tools

Wolfram Alpha pairs well with:
- **Web search**: For context around computational results
- **LLM**: For explaining or elaborating on outputs
- **Vision**: For analyzing data visualizations

## Minimal Usage Heuristic

For symbolic math, write queries more like a CAS (Computer Algebra System) command than a chat message. Keep it compact and precise.
