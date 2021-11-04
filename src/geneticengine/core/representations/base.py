from typing import Any, Callable, Generic, TypeVar, Tuple
from dataclasses import dataclass
from geneticengine.core.random.sources import RandomSource
from geneticengine.core.grammar import Grammar

t = TypeVar("t")


@dataclass
class Representation(Generic[t]):
    create_individual: Callable[[RandomSource, Grammar, int], t]
    mutate_individual: Callable[[RandomSource, Grammar, t, int], t]
    crossover_individuals: Callable[[RandomSource, Grammar, t, t, int], Tuple[t, t]]
