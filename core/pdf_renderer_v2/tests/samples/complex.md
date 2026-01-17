# Complex Test Document

This document tests all Markdown features.

## Chapter 1: Text Formatting

Regular paragraph with **bold**, *italic*, ***bold italic***, ~~strikethrough~~, and `inline code`.

### Subscript and Superscript

Water: H~2~O

Einstein: E=mc^2^

## Chapter 2: Lists

### Unordered List

- First item
  - Nested item 1
  - Nested item 2
- Second item
- Third item

### Ordered List

1. First step
2. Second step
   1. Sub-step A
   2. Sub-step B
3. Third step

### Definition List

Term 1
:   Definition of term 1

Term 2
:   Definition of term 2

## Chapter 3: Code Blocks

### Python

```python
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

# Calculate first 10 Fibonacci numbers
for i in range(10):
    print(fibonacci(i))
```

### JavaScript

```javascript
const greet = (name) => {
    return `Hello, ${name}!`;
};

console.log(greet("World"));
```

## Chapter 4: Tables

### Simple Table

| Header 1 | Header 2 | Header 3 |
|----------|----------|----------|
| Cell 1   | Cell 2   | Cell 3   |
| Cell 4   | Cell 5   | Cell 6   |

### Aligned Table

| Left | Center | Right |
|:-----|:------:|------:|
| L1   | C1     | R1    |
| L2   | C2     | R2    |

## Chapter 5: Blockquotes

> This is a simple blockquote.

> This is a multi-paragraph blockquote.
>
> It has multiple paragraphs.
>
> > And nested quotes too.

## Chapter 6: Links and Images

[This is a link](https://example.com)

[This is a link with title](https://example.com "Example Title")

## Chapter 7: Horizontal Rules

Above the rule.

---

Below the rule.

***

Another rule style.

## Chapter 8: Footnotes

Here is a sentence with a footnote[^1].

And another one[^2].

[^1]: This is the first footnote.
[^2]: This is the second footnote with more text.

## Conclusion

This document has tested:

1. Text formatting
2. Lists (ordered, unordered, definition)
3. Code blocks
4. Tables
5. Blockquotes
6. Links
7. Horizontal rules
8. Footnotes

**End of document.**
