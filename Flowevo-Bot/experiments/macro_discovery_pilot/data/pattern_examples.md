# 真实模式例子与范围

## root_invariants
### math_train_algebra_1366

题目：What is the sum of the roots of $x^2 - 4x + 3 = 0$?

实际模型解法：

For the quadratic equation \(x^2 - 4x + 3 = 0\), the sum of the roots is given by Vieta's formula:

\[
\text{Sum of roots} = -\frac{b}{a}
\]

Here, \(a = 1\) and \(b = -4\), so:

\[
\text{Sum} = -\frac{-4}{1} = 4
\]

The answer is 4.

来源SHA：0b645c61707ae80c1fa6565d2d8a3e6058cad745147ef2da0923c8ce1a0fd5f9

### math_train_intermediate_algebra_1007

题目：Let $a,$ $b,$ $c$ be the roots of $3x^3 - 3x^2 + 11x - 8 = 0.$  Find $ab + ac + bc.$

实际模型解法：

For the cubic equation
\[
3x^3 - 3x^2 + 11x - 8 = 0,
\]
the roots are \(a,b,c\).

By Vieta’s formulas, for
\[
Ax^3+Bx^2+Cx+D=0,
\]
the sum of pairwise products of the roots is
\[
ab+ac+bc=\frac{C}{A}.
\]

Here, \(A=3\) and \(C=11\), so
\[
ab+ac+bc=\frac{11}{3}.
\]

The answer is \(\boxed{\frac{11}{3}}\).

来源SHA：88cdb6c16d70c58e149996069d134d299e1b196accd6278fc3b0b301c4880654

### math_train_intermediate_algebra_1151

题目：Find the product of the roots of the equation \[(2x^3 + x^2 - 8x + 20)(5x^3 - 25x^2 + 19) = 0.\]

实际模型解法：

For a cubic equation
\[
ax^3+bx^2+cx+d=0,
\]
the product of its roots is
\[
-\frac{d}{a}.
\]

For the first factor:
\[
2x^3+x^2-8x+20=0
\]
the product of its roots is
\[
-\frac{20}{2}=-10.
\]

For the second factor:
\[
5x^3-25x^2+19=0
\]
the product of its roots is
\[
-\frac{19}{5}.
\]

Since the original equation is the product of these two cubics, its roots are the roots of both factors combined. Therefore, the product of all roots is
\[
(-10)\left(-\frac{19}{5}\right)=38.
\]

The answer is 38.

来源SHA：77b156bfbbe25ceead990a45490bf12cc57c2bc1a9ca1cbd1970b24d1b407268

### math_train_intermediate_algebra_742

题目：Let $a,$ $b,$ $c,$ and $d$ be the roots of \[x^4 + 8x^3 + 9x^2 + 5x + 4 = 0.\]Find the value of \[\frac{1}{ab} + \frac{1}{ac} + \frac{1}{ad} + \frac{1}{bc} + \frac{1}{bd} + \frac{1}{cd}.\]

实际模型解法：

By Vieta’s formulas for the quartic
\[
x^4+8x^3+9x^2+5x+4=0,
\]
if its roots are \(a,b,c,d\), then
\[
ab+ac+ad+bc+bd+cd=9
\]
and
\[
abcd=4.
\]

Now,
\[
\frac{1}{ab}+\frac{1}{ac}+\frac{1}{ad}+\frac{1}{bc}+\frac{1}{bd}+\frac{1}{cd}
\]
can be written using common denominator \(abcd\):
\[
=\frac{cd+bd+bc+ad+ac+ab}{abcd}
=\frac{ab+ac+ad+bc+bd+cd}{abcd}.
\]
Thus,
\[
= \frac{9}{4}.
\]

The answer is \(\boxed{\frac94}\).

来源SHA：96a7782ad9c09be44d44646c3c7a9bd2ced469b19ae555a3896b8b98a8e1a310

### math_train_intermediate_algebra_918

题目：Let $a,$ $b,$ $c$ be the roots of the cubic $x^3 + 3x^2 + 5x + 7 = 0.$  Given that $P(x)$ is a cubic polynomial such that $P(a) = b + c,$ $P(b) = a + c,$ $P(c) = a + b,$ and $P(a + b + c) = -16,$ find $P(x).$

实际模型解法：

By Vieta’s formulas for  
\[
x^3+3x^2+5x+7=0,
\]
we have
\[
a+b+c=-3,\qquad ab+bc+ca=5,\qquad abc=-7.
\]
Thus
\[
b+c=(-3)-a=-a-3,
\]
and similarly
\[
P(a)=-a-3,\quad P(b)=-b-3,\quad P(c)=-c-3.
\]
So \(P(x)-(-x-3)=P(x)+x+3\) vanishes at \(a,b,c\). Therefore it is divisible by
\[
(x-a)(x-b)(x-c)=x^3+3x^2+5x+7.
\]
Since \(P(x)+x+3\) is cubic, it must be a constant multiple of this cubic:
\[
P(x)+x+3=k(x^3+3x^2+5x+7).
\]
Hence
\[
P(x)=k(x^3+3x^2+5x+7)-x-3.
\]

Now use \(P(a+b+c)=P(-3)=-16\). First,
\[
(-3)^3+3(-3)^2+5(-3)+7=-8.
\]
So
\[
P(-3)=k(-8)-(-3)-3=-8k=-16,
\]
giving \(k=2\).

Therefore,
\[
P(x)=2(x^3+3x^2+5x+7)-x-3
\]
\[
=2x^3+6x^2+10x+14-x-3
\]
\[
=2x^3+6x^2+9x+11.
\]

The answer is \(\boxed{2x^3+6x^2+9x+11}\).

来源SHA：a23ee989dacc0988b24c184ed4637239a531c29de269bc212e752a6c8e0335a7

### math_train_intermediate_algebra_955

题目：Compute the product of the roots of the equation \[x^3 - 12x^2 + 48x + 28 = 0.\]

实际模型解法：

For a cubic equation of the form

\[
x^3 - 12x^2 + 48x + 28 = 0,
\]

let the roots be \(r_1, r_2, r_3\).

By Vieta’s formulas, the product of the roots is

\[
r_1 r_2 r_3 = -\frac{\text{constant term}}{\text{leading coefficient}}.
\]

Here, the constant term is \(28\), and the leading coefficient is \(1\). Therefore,

\[
r_1 r_2 r_3 = -\frac{28}{1} = -28.
\]

The answer is -28.

来源SHA：f7b0c05c91d9f8c62f0f83b3d8d40d865a35083949194de106ce96a0f067e45f

## polynomial_remainder
### math_train_intermediate_algebra_738

题目：Find the remainder when $6x^4-14x^3-4x^2+2x-26$ is divided by $2x - 6.$

实际模型解法：

To find the remainder when dividing by \(2x-6\), use the Remainder Theorem.

Let  
\[
P(x)=6x^4-14x^3-4x^2+2x-26
\]
The divisor \(2x-6=0\) gives:
\[
2x-6=0 \implies x=3
\]
So the remainder is \(P(3)\):
\[
P(3)=6(3)^4-14(3)^3-4(3)^2+2(3)-26
\]
\[
=6(81)-14(27)-4(9)+6-26
\]
\[
=486-378-36+6-26
\]
\[
=52
\]

The answer is 52.

来源SHA：ad2ddd3ef279fe8e29b09a3da78ca04a9a288936fec9552ef8f55188c9f63144

### math_train_intermediate_algebra_891

题目：Determine the remainder when $(x^4-1)(x^2-1)$ is divided by $1+x+x^2$.

实际模型解法：

Work modulo \(1+x+x^2\). Since
\[
x^2+x+1=0 \implies x^2\equiv -x-1,
\]
we also get
\[
x^3\equiv x(-x-1)=-x^2-x\equiv -(-x-1)-x=1,
\]
so
\[
x^4\equiv x.
\]

Now compute:
\[
(x^4-1)(x^2-1)\equiv (x-1)((-x-1)-1)
\]
\[
=(x-1)(-x-2)
=-x^2-x+2.
\]
Using \(x^2\equiv -x-1\),
\[
-x^2-x+2\equiv -(-x-1)-x+2=x+1-x+2=3.
\]

Thus the remainder is \(3\).

The answer is 3.

来源SHA：6873185fcebd85d603ac2b033b52f5be3308c788c47fc0d5434069ab4d63e7a9
