# Execution Prompt Generator

This file generates actionable prompts that execute tasks using real data sources.

## Overview

**Two-step process:**

1. **Planning Phase**: Use `decomposition.md` to create execution plans in `Plan/` directory
2. **Execution Phase**: Use this meta-prompt to generate task-specific prompts in `Prompts/` directory

## Step 1: Generate Plan Files

Run `decomposition.md` with your user request to create:
- `Plan/FinalArtifactSpec.json` - What to produce
- `Plan/DataSources.json` - Where to get data
- `Plan/DataSchema.json` - Data structure
- `Plan/ExecutionPlan.json` - Execution order
- `Plan/ValidationRules.json` - Quality checks

## Step 2: Generate Execution Prompts

Use this prompt to generate executable task prompts:

```text
Read these plan files:
- Plan/FinalArtifactSpec.json
- Plan/DataSources.json
- Plan/DataSchema.json
- Plan/ExecutionPlan.json
- Plan/ValidationRules.json

Generate execution prompts that:
1. Use REAL data sources (APIs, web scraping, etc.)
2. Include validation steps to detect fake data
3. Handle errors and edge cases
4. Save results to Artifacts/ directory
5. Are completely self-contained

For each step in ExecutionPlan.json, create a prompt file.
```

## Prompt Template

Each execution prompt should follow this structure:

```text
# Task: [Step Name]

## Objective
[Clear, one-sentence goal]

## Data Sources
[Specific APIs, URLs, or methods from DataSources.json]
- Endpoint: [exact URL or location]
- Method: [API call, CSS selector, etc.]
- Authentication: [if needed]

## Input Requirements
[What data/files must exist before running]
- Check for: Artifacts/[dependencies].json
- If missing: STOP with error message

## Execution Steps
1. [Concrete action with tool/method]
2. [Next action]
3. Validate results:
   - [Specific check]
   - [How to detect fake data]
4. Save to: Artifacts/[output].json

## Output Schema
```json
{
  "field1": "value",
  "field2": 123
}
```

## Validation
- [ ] Field X matches regex: [pattern]
- [ ] URL Y returns 200 OK
- [ ] Count >= [minimum]
- [ ] No placeholder/fake data

## Error Handling
- If API fails: [fallback]
- If validation fails: [action]
- If data missing: [action]

## Success Criteria
[How to know it worked]
```

## Critical Rules

### Every Prompt Must:
- Specify EXACT data sources (URLs, APIs, selectors)
- Include HTTP requests to validate data (e.g., check if website exists)
- Save output to `Artifacts/[id].json`
- Stop execution on validation failure
- Never invent or hallucinate data

### Anti-Hallucination Measures:
- Verify URLs with HTTP HEAD requests
- Check email format with regex
- Validate phone numbers against known patterns
- Cross-reference data from multiple sources
- Flag any data that can't be verified

## Output Structure

Generate these files:

### 1. Prompts/00_system_prompt.txt
System instructions for all task executions:
```text
You are a data collection and validation agent.

CORE RULES:
- Use ONLY real data sources (APIs, web scraping, databases)
- NEVER invent or hallucinate data
- Validate all data before saving
- Stop on validation failure
- Save results to Artifacts/ directory

DATA VALIDATION:
- URLs: Check with HTTP HEAD request (must return 2xx)
- Emails: Validate format with regex
- Phones: Check format against patterns
- Names/Addresses: Cross-reference when possible

ERROR HANDLING:
- API failure: Use fallback source or report error
- Validation failure: Report specific issue, do not proceed
- Missing dependencies: Stop with clear error message

OUTPUT FORMAT:
All outputs must be valid JSON saved to Artifacts/[task_id].json
```

### 2. Prompts/TaskIndex.json
Execution tracking and sequencing:
```json
{
  "version": "1.0",
  "generated_at": "[ISO-8601 timestamp]",
  "tasks": [
    {
      "id": "task_1",
      "name": "[Task name]",
      "prompt_file": "Prompts/P_task_1.txt",
      "output_file": "Artifacts/task_1.json",
      "depends_on": [],
      "status": "pending"
    }
  ],
  "execution_order": ["task_1", "task_2", "..."]
}
```

### 3. Individual Task Prompts
One file per task: `Prompts/P_[task_id].txt`

Each prompt includes:
- Clear objective
- Specific data sources with URLs/endpoints
- Input dependencies (files that must exist)
- Execution steps with validation
- Output schema
- Error handling
- Success criteria

## Example Task Prompt

```text
# Task: Find Businesses Without Websites in Montería

## Objective
Identify 5 businesses in Montería, Colombia that don't have websites.

## Data Sources

### Primary: Google Maps API
- Endpoint: https://maps.googleapis.com/maps/api/place/textsearch/json
- Query: "businesses in Montería, Colombia"
- Fields: name, address, phone, place_id
- Rate limit: 1 request/second
- API Key: [from environment or config]

### Validation: Website Check
- For each business, search: "[business name] [city] website"
- Check URLs with HTTP HEAD request
- If 2xx response: business HAS website, skip
- If 4xx/5xx/timeout: business likely has NO website, include

## Input Requirements
None (this is first task)

## Execution Steps

1. Query Google Maps API:
   ```
   GET https://maps.googleapis.com/maps/api/place/textsearch/json?query=businesses+Montería+Colombia&key=[API_KEY]
   ```

2. For each result (up to 20):
   a. Extract: name, address, phone
   b. Search web for: "[name] sitio web"
   c. Test each URL found with HTTP HEAD
   d. If no working URL: add to results
   e. Stop when 5 businesses found

3. Validate each business:
   - Name not empty
   - Address contains "Montería"
   - Phone matches Colombian format (+57 XXX XXX XXXX)
   - Confirmed no working website

4. Save to: Artifacts/businesses_no_website.json

## Output Schema
```json
{
  "task_id": "businesses_no_website",
  "timestamp": "2026-02-27T10:00:00Z",
  "count": 5,
  "businesses": [
    {
      "name": "string",
      "address": "string",
      "phone": "string",
      "verified_no_website": true,
      "search_attempted": "2026-02-27T10:00:00Z"
    }
  ],
  "status": "completed"
}
```

## Validation Checklist
- [ ] Exactly 5 businesses
- [ ] All in Montería
- [ ] All phone numbers valid format
- [ ] Website check performed for each
- [ ] No placeholder data (e.g., "123-456-7890", "example@email.com")

## Error Handling
- If API fails: Stop and report error (no fallback for this critical source)
- If < 5 found after 20 results: Report partial results with count
- If validation fails: Report which business failed and why

## Success Criteria
- 5 valid businesses saved to Artifacts/businesses_no_website.json
- All validation checks pass
- File is valid JSON
```

## Generating Prompts

To generate all prompts from your plan files:

1. Read ExecutionPlan.json
2. For each step, create a P_[id].txt file following the template
3. Use DataSources.json for specific endpoints/methods
4. Use DataSchema.json for output structure
5. Use ValidationRules.json for checks
6. Update TaskIndex.json with all tasks

## Final Notes

**Quality over complexity:**
- Simple, executable prompts > elaborate frameworks
- Real data sources > theoretical pipelines
- Concrete validation > abstract contracts
- Error messages > silent failures

**Each prompt must answer:**
- WHERE exactly to get data?
- HOW exactly to validate it?
- WHAT to do if it fails?
- WHERE to save the result?
