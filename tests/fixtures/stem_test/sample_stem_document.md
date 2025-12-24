# Sample STEM Document for E2E Testing

This document tests the complete pipeline from detection to export.

## 1. Mathematical Formulas

### 1.1 Inline Formulas

The famous equation $E = mc^2$ shows mass-energy equivalence.
In quantum mechanics, we have the Schrödinger equation with $\psi(x,t)$.
The quadratic formula is $x = \frac{-b \pm \sqrt{b^2-4ac}}{2a}$.

### 1.2 Display Formulas

The integral of a Gaussian function:

$$\int_{-\infty}^{\infty} e^{-x^2} dx = \sqrt{\pi}$$

Maxwell's equations in differential form:

$$\nabla \cdot \mathbf{E} = \frac{\rho}{\epsilon_0}$$

$$\nabla \times \mathbf{B} = \mu_0 \mathbf{J} + \mu_0 \epsilon_0 \frac{\partial \mathbf{E}}{\partial t}$$

## 2. Code Blocks

### 2.1 Python Code

```python
def calculate_energy(mass: float, c: float = 299792458) -> float:
    """Calculate energy using E=mc^2."""
    return mass * c ** 2

# Example usage
energy = calculate_energy(1.0)
print(f"Energy: {energy:.2e} Joules")
```

### 2.2 JavaScript Code

```javascript
function fibonacci(n) {
    if (n <= 1) return n;
    return fibonacci(n - 1) + fibonacci(n - 2);
}

// Generate first 10 Fibonacci numbers
const sequence = Array.from({length: 10}, (_, i) => fibonacci(i));
console.log(sequence);
```

### 2.3 SQL Query

```sql
SELECT
    u.name,
    COUNT(o.id) as order_count,
    SUM(o.total) as total_spent
FROM users u
LEFT JOIN orders o ON u.id = o.user_id
WHERE o.created_at > '2024-01-01'
GROUP BY u.id
HAVING total_spent > 1000
ORDER BY total_spent DESC;
```

### 2.4 Inline Code

Use the `print()` function in Python. The variable `x` holds the value.
Call `fibonacci(10)` to get the 10th Fibonacci number.

## 3. Chemical Formulas

Water is H2O. Carbon dioxide is CO2. Glucose has the formula C6H12O6.

The combustion of methane:
CH4 + 2O2 → CO2 + 2H2O

Photosynthesis equation:
6CO2 + 6H2O → C6H12O6 + 6O2

## 4. Tables

### 4.1 Physical Constants

| Constant | Symbol | Value | Unit |
|----------|--------|-------|------|
| Speed of light | c | 299,792,458 | m/s |
| Planck constant | h | 6.626 × 10⁻³⁴ | J·s |
| Gravitational constant | G | 6.674 × 10⁻¹¹ | m³/(kg·s²) |
| Boltzmann constant | k | 1.381 × 10⁻²³ | J/K |

### 4.2 Programming Languages

| Language | Paradigm | Typing | Use Case |
|----------|----------|--------|----------|
| Python | Multi-paradigm | Dynamic | Data Science, Web |
| Rust | Systems | Static | Performance-critical |
| JavaScript | Event-driven | Dynamic | Web Development |
| Go | Concurrent | Static | Cloud Services |

## 5. Lists

### 5.1 Bullet List

Key concepts in machine learning:
- Supervised learning
  - Classification
  - Regression
- Unsupervised learning
  - Clustering
  - Dimensionality reduction
- Reinforcement learning
  - Q-learning
  - Policy gradient

### 5.2 Numbered List

Steps to train a neural network:
1. Prepare the dataset
2. Define the model architecture
3. Choose loss function and optimizer
4. Train the model
   1. Forward pass
   2. Calculate loss
   3. Backward pass
   4. Update weights
5. Evaluate on test data
6. Fine-tune hyperparameters

## 6. Blockquotes

> "The important thing is not to stop questioning. Curiosity has its own reason for existence."
> — Albert Einstein

> In the middle of difficulty lies opportunity.
> — Albert Einstein

## 7. Mixed Content

The **Pythagorean theorem** states that in a right triangle, $a^2 + b^2 = c^2$.

Here's a Python implementation:

```python
import math

def pythagorean(a: float, b: float) -> float:
    """Calculate hypotenuse using Pythagorean theorem."""
    return math.sqrt(a**2 + b**2)

# Example: 3-4-5 triangle
c = pythagorean(3, 4)
print(f"Hypotenuse: {c}")  # Output: 5.0
```

The result for a 3-4-5 triangle is `c = 5.0`.

---

## Conclusion

This document demonstrates the preservation of:
- Mathematical formulas (inline and display)
- Code blocks (multiple languages)
- Chemical formulas
- Tables
- Lists (bullet and numbered)
- Blockquotes
- Mixed content

End of test document.
