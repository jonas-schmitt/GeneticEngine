from dataclasses import dataclass
from typing import Any, Callable
from geneticengine.grammars.coding.classes import Expr, Condition


@dataclass
class Equals(Condition):
    left: Expr
    right: Expr

    def evaluate(self, **kwargs) -> bool:
        return self.left.evaluate(**kwargs) == self.right.evaluate(**kwargs)

    def evaluate_lines(self, **kwargs) -> Callable[[Any], bool]:
        return lambda line: self.left.evaluate_lines(**kwargs)(
            line
        ) == self.right.evaluate_lines(**kwargs)(line)

    def __str__(self):
        return f"({self.left} == {self.right})"


@dataclass
class NotEquals(Condition):
    left: Expr
    right: Expr

    def evaluate(self, **kwargs) -> bool:
        return self.left.evaluate(**kwargs) != self.right.evaluate(**kwargs)

    def evaluate_lines(self, **kwargs) -> Callable[[Any], bool]:
        return lambda line: self.left.evaluate_lines(**kwargs)(
            line
        ) != self.right.evaluate_lines(**kwargs)(line)

    def __str__(self):
        return f"({self.left} != {self.right})"


@dataclass
class GreaterThan(Condition):
    left: Expr
    right: Expr

    def evaluate(self, **kwargs) -> bool:
        return self.left.evaluate(**kwargs) > self.right.evaluate(**kwargs)

    def evaluate_lines(self, **kwargs) -> Callable[[Any], bool]:
        return lambda line: self.left.evaluate_lines(**kwargs)(
            line
        ) > self.right.evaluate_lines(**kwargs)(line)

    def __str__(self):
        return f"({self.left} > {self.right})"


@dataclass
class GreaterOrEqualThan(Condition):
    left: Expr
    right: Expr

    def evaluate(self, **kwargs) -> bool:
        return self.left.evaluate(**kwargs) >= self.right.evaluate(**kwargs)

    def evaluate_lines(self, **kwargs) -> Callable[[Any], bool]:
        return lambda line: self.left.evaluate_lines(**kwargs)(
            line
        ) >= self.right.evaluate_lines(**kwargs)(line)

    def __str__(self):
        return f"({self.left} >= {self.right})"


@dataclass
class LessThan(Condition):
    left: Expr
    right: Expr

    def evaluate(self, **kwargs) -> bool:
        return self.left.evaluate(**kwargs) < self.right.evaluate(**kwargs)

    def evaluate_lines(self, **kwargs) -> Callable[[Any], bool]:
        return lambda line: self.left.evaluate_lines(**kwargs)(
            line
        ) < self.right.evaluate_lines(**kwargs)(line)

    def __str__(self):
        return f"({self.left} < {self.right})"


@dataclass
class LessOrEqualThan(Condition):
    left: Expr
    right: Expr

    def evaluate(self, **kwargs) -> bool:
        return self.left.evaluate(**kwargs) <= self.right.evaluate(**kwargs)

    def evaluate_lines(self, **kwargs) -> Callable[[Any], bool]:
        return lambda line: self.left.evaluate_lines(**kwargs)(
            line
        ) <= self.right.evaluate_lines(**kwargs)(line)

    def __str__(self):
        return f"({self.left} <= {self.right})"


@dataclass
class Is(Condition):
    left: Expr
    right: Expr

    def evaluate(self, **kwargs) -> bool:
        return self.left.evaluate(**kwargs) is self.right.evaluate(**kwargs)

    def evaluate_lines(self, **kwargs) -> Callable[[Any], bool]:
        return lambda line: self.left.evaluate_lines(**kwargs)(
            line
        ) is self.right.evaluate_lines(**kwargs)(line)

    def __str__(self):
        return f"({self.left} is {self.right})"


@dataclass
class IsNot(Condition):
    left: Expr
    right: Expr

    def evaluate(self, **kwargs) -> bool:
        return self.left.evaluate(**kwargs) is not self.right.evaluate(**kwargs)

    def evaluate_lines(self, **kwargs) -> Callable[[Any], bool]:
        return lambda line: self.left.evaluate_lines(**kwargs)(
            line
        ) is not self.right.evaluate_lines(**kwargs)(line)

    def __str__(self):
        return f"({self.left} is not {self.right})"


all_operators = [
    Equals,
    NotEquals,
    GreaterOrEqualThan,
    GreaterThan,
    LessOrEqualThan,
    LessThan,
    Is,
    IsNot,
]
