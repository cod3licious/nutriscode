# Nutri-SCode: Compute a Nutri-Score for Your Code

A static analysis tool that ranks functions by their **computational density**: the ratio of meaningful work (arithmetic, decisions, logic) to structural volume (statements). Functions with low scores are candidates for simplification or removal; functions with high scores are doing real work and deserve attention when something goes wrong.

A Python script using the tree-sitter library analyzes a repository to count the statements and computations of each function, with results saved in a JSON file. This file can then be loaded by `index.html` to display the results as a scatter plot that shows the functions' weighted sum of their computations against the number of statements. Additionally, combined results from all functions in the codebase are derived to make it possible to compare whole repositories in a similar fashion.

**You can find a demo comparing several popular Python packages [here](https://franziskahorn.de/demo_nutriscode/):**

![](https://franziskahorn.de/demo_nutriscode/nutriscode_ui.png)

### The Problem This Solves

Most approaches to identifying technical debt focus on *structural* properties: cyclic dependencies, coupling between modules, inconsistent layering. These are real problems, but they miss a different class of issues: code that is structurally clean but contains more ceremony than substance.

A codebase can have perfect modularity scores and still be exhausting to work in because a large fraction of its functions are boilerplate: DTOs that mirror each other field-for-field, mappers that rename fields between identical representations, service classes that do nothing but delegate to a single other function, pass-through wrappers that exist to satisfy an abstraction that doesn't earn its keep. None of this shows up as a structural violation. It just makes every change touch more files than it should.

Nutri-SCode addresses this by asking a different question: **not where the code is structured badly, but where the code is doing less than its volume implies**.

## The Core Idea

Every function has a ratio between the *decisions and computations* it encodes and the *structural volume* it occupies. A function that copies ten fields from one object to another has low density — lots of statements, no meaningful operations. A function that fits a machine learning model, calculates an evaluation metric, or implements a pricing engine has high density — every line is doing real work.

This is analogous to nutritional density in food: a function full of boilerplate is empty calories — it takes up space in your codebase but contributes little computational value. The score surfaces these functions so you can ask whether they need to exist at all.

The score for a function is:

```
score = weighted_sum_of_operations / max(statement_count, 1)
```

Though normally you'd just look at the operation vs. statement counts directly in a scatter plot. 

The coefficients for the weighted sum are configurable in the web app with the following default values:

| Element | Weight | Rationale |
|---------|--------|-----------|
| Math operations (`+`, `-`, `*`, `/`, `**`, `%`, etc.) | 1.0 | Unambiguous computation |
| Bitwise operations (`&`, `\|`, `^`, `~`, `<<`, `>>`) | 0.9 | Other fancy computations |
| Conditionals & pattern matches (`if`, `else`, `switch`, `match`) | 0.4 | Encode branching decisions |
| Logical operators (`and`, `or`, `not`, `&&`, `\|\|`) | 0.6 | Boolean logic, indicates more complicated decisions |
| Comparisons (`==`, `!=`, `<`, `>`, `<=`, `>=`) | 0.5 | Encode decisions in expression form |
| Function calls | 0.3 × max(0, count − 1) | First call is free (a single-call function is a wrapper by definition); subsequent calls count |
| Assertions (`assert`) | 0.2 | Encode invariants; count higher when combined with comparisons |
| Exception handlers (`catch`, `except`, `finally`) | 0.1 | Control flow, but rarely encodes domain logic |


### Interpreting the Score

The score is most useful as a **ranking** rather than an absolute value. There is no universal threshold for "good" or "bad" — what matters is the distribution within your codebase.

As rough orientation:

- **Score = 0.0**: No operations at all. Pure field assignments, empty constructors, getters. Almost always ceremony.
- **Score < 0.2**: Very low density. Likely pass-throughs, thin wrappers, or simple delegation. Worth reviewing whether these functions earn their existence.
- **Score 0.2–0.5**: Moderate density. Orchestration, simple conditional logic, light processing. Context-dependent.
- **Score > 0.5**: Meaningful density. Real computation or decision logic is present.
- **Score > 1.0**: High density. The function does significant work per statement — mathematical computation, complex conditionals, or both.

The bottom 10–15% of functions by score in a typical enterprise codebase are the most productive targets for a "do we need this?" review.

### What This Tool Does Not Catch

The score identifies ceremony by its absence of operations. It does not identify:

- **Correct structure, wrong boundaries** — modules that are internally clean but decomposed along the wrong axis (use Tornhill's change coupling analysis for this)
- **Cyclic dependencies and erosion** — structural health of the module graph (use tools like Sonargraph or ArchUnit)
- **Complex code that should be simpler** — high-scoring functions that implement something complex because of a poor approach rather than genuine problem complexity (requires human review)
- **Operator overloading and string concatenation** — the AST cannot distinguish `a + b` on numbers from `a + b` on strings, so string concatenation with `+`/`+=` is counted as a math operation, slightly inflating scores for functions that build strings with `+` instead of f-strings or `.join()`
- **Logic hidden in SQL strings, regex patterns, or other embedded DSLs** — string literals are opaque to the AST parser

It is intended to complement, not replace, structural analysis and behavioral analysis (commit frequency, change coupling).


## Getting started

Give it a try and analyze the nutritional value of your own codebase!

### Installation

It is recommended to use [uv](https://docs.astral.sh/uv/) to install the dependencies and run the script in a virtual environment.

You can install the needed tree-sitter packages with

```bash
uv sync
```

or install only what you need directly:

```bash
pip install tree-sitter tree-sitter-python tree-sitter-javascript \
            tree-sitter-typescript tree-sitter-java tree-sitter-go
```

Feel free to skip dependencies for languages you don't need - unsupported languages are silently ignored.

### Usage

Analyze a codebase with

```bash
uv run src/analyze_repo.py <path> <extension> [--min-statements <n>]
```

This will create a folder `results/` in the root directory (if one does not already exist) where the scores for the codebase are saved under `<repository>.json` (possibly overwriting any existing file by that name). Additionally, a file by the name `_all.json` is created or extended to add an entry with the summary statistics for the analyzed repository.

**Arguments:**

| Argument | Description |
|----------|-------------|
| `path` | Root directory of the codebase to analyse |
| `extension` | File extension to scan (`py`, `ts`, `js`, `java`, `go`) |
| `--min-statements` | Exclude functions with fewer statements (default: 0) |

**Examples:**

```bash
# Analyze a TypeScript project
uv run src/analyze_repo.py ./myproject ts

# Analyze a Java project and raise the minimum statement threshold to reduce noise
uv run src/analyze_repo.py ./myproject java --min-statements 2
```

**Run the tests:**

```bash
uv run pytest
```

### Running the frontend

Open `index.html` in a browser served by any static file server. You can select one of the jsons from the `results/` directory to render the scatter plot.

```bash
# simple local server, no installation required
python -m http.server 8000
# then open http://localhost:8000
```

### Supported Languages

| Extension | Language | Parser package |
|-----------|----------|---------------|
| `py` | Python | `tree-sitter-python` |
| `js` / `ts` | JavaScript and TypeScript (incl. `.jsx` and `.tsx` files) | `tree-sitter-javascript` & `tree-sitter-typescript` |
| `java` | Java | `tree-sitter-java` |
| `go` | Go | `tree-sitter-go` |

Adding a new language requires installing its tree-sitter package and adding a `LanguageConfig` entry mapping its AST node types to the metric categories. No changes to the scoring logic are needed.

---

## Design Decisions

#### Statement count as the denominator, not LOC

Lines of code varies with formatting style and is meaningless across languages. Statement count is a better proxy for structural volume because it counts units of execution regardless of how they are laid out. A chained expression on one line and the same logic spread across five lines produce the same statement count.

#### Lambdas are counted inline in their enclosing function

A lambda passed as an argument to `sorted()` or `filter()` is part of the calling function's logic. Scoring it separately would make the enclosing function appear emptier than it is. Lambda operations are attributed to the nearest enclosing named function.

#### Nested named functions are scored separately

A named function defined inside another function is an independent unit of logic and gets its own score entry. This prevents inner functions from inflating their parent's score.

#### No recursive call propagation

An obvious extension would be to propagate nutritional value up through call chains — a wrapper calling a nutritious function would score higher than a wrapper calling another empty wrapper. This was considered and rejected because it causes orchestrator functions (which do nothing but sequence calls) to score very high, which is backwards: they are precisely the functions you want to identify as low-substance. It also creates double-counting problems when a utility function is called from many places. The current approach scores what *this function itself does*, not what it triggers downstream.

#### Call credit starts at the second call

A function with a single call and no other logic is definitionally a pass-through wrapper — it should score zero regardless of what it calls. The `max(0, count − 1)` formula ensures this. A function with two or more calls starts accumulating credit, reflecting that coordinating multiple operations is doing something even if each individual call is opaque.

#### No internal vs. external call distinction

Distinguishing library calls from own-code calls and to give them different weights would be nice, but requires module resolution, which is language-specific and adds significant implementation complexity. A single unified call coefficient is a pragmatic simplification. The accuracy loss is small: the call coefficient is intentionally modest (0.3) and only applies from the second call onward, so it rarely dominates a function's score.

#### Tree-sitter as the parsing backend

Tree-sitter provides production-quality parsers for 40+ languages through a consistent API. Using it as the parsing layer means the scoring logic is entirely language-agnostic — the language-specific work is limited to mapping each language's AST node types to the metric categories. Adding a new language requires only a new `LanguageConfig` mapping, not changes to the scorer.

#### Output Format

A JSON dictionary of function entries, sorted alphabetically:

```json
{
  "orders.service.OrderService.create": {
    "statement_count": 8,
    "math_ops": 0,
    "bitwise_ops": 0,
    "conditionals": 1,
    "logical_ops": 0,
    "comparisons": 0,
    "calls": 3,
    "assertions": 0,
    "exception_handlers": 0
  }
}
```

The key is the function's dotted path derived from the file's path relative to the project root, the class name (if any), and the function name. Uninformative path segments (`__init__`, `index`, `src`, `lib`, `mod`) are omitted.

In the `_all.json` file, the key is the repository name.
