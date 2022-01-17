from dataclasses import dataclass
import sys
from copy import deepcopy
from itertools import accumulate

from typing import (
    Any,
    Callable,
    Dict,
    NoReturn,
    Set,
    Type,
    TypeVar,
    Tuple,
    List,
    Union,
)

from geneticengine.core.decorators import get_gengy, is_builtin
from geneticengine.core.random.sources import RandomSource, Source
from geneticengine.core.grammar import Grammar
from geneticengine.core.representations.api import Representation
from geneticengine.core.tree import TreeNode
from geneticengine.core.utils import (
    get_arguments,
    is_generic_list,
    get_generic_parameter,
    is_terminal,
)
from geneticengine.exceptions import GeneticEngineError
from geneticengine.metahandlers.base import MetaHandlerGenerator


def random_int(r: Source) -> int:
    return r.randint(-(sys.maxsize - 1), sys.maxsize)


def random_float(r: Source) -> float:
    return r.random_float(-100, 100)


T = TypeVar("T")


def random_list(
    r: Source,
    g: Grammar,
    wrapper: Callable[[Any, str, int, Callable[[int], Any]], Any],
    rec: Any,
    depth: int,
    ty: Type[List[T]],
):
    inner_type = get_generic_parameter(ty)
    size = r.randint(0, depth - 1)
    return [rec(r, g, wrapper, depth - 1, inner_type) for _ in range(size)]


def is_metahandler(ty: type) -> bool:
    """
    Returns if type is a metahandler.
    AnnotatedType[int, IntRange(3,10)] is an example of a Metahandler.

    Verification is done using the __metadata__, which is the first argument of Annotated
    """
    return hasattr(ty, "__metadata__")


def apply_metahandler(
    r: Source,
    g: Grammar,
    wrapper: Callable[[Any, str, int, Callable[[int], Any]], Any],
    rec: Callable[[RandomSource, Grammar, Any, Any, int, Any], Any],
    depth: int,
    ty: Type[Any],
    argn: str,
    context: Dict[str, Type],
) -> Any:
    """
    This method applies a metahandler to use a custom generator for things of a given type.

    As an example, AnnotatedType[int, IntRange(3,10)] will use the IntRange.generate(r, recursive_generator)

    The generator is the annotation on the type ("__metadata__").
    """
    metahandler: MetaHandlerGenerator = ty.__metadata__[0]
    base_type = get_generic_parameter(ty)
    if is_generic_list(base_type):
        base_type = get_generic_parameter(base_type)
    return metahandler.generate(r, g, wrapper, rec, depth, base_type, argn, context)


def filter_choices(g: Grammar, possible_choices: List[type], depth):
    valid_productions = [
        vp for vp in possible_choices if g.distanceToTerminal[vp] <= depth
    ]
    if any(  # Are we the last recursive symbol?
        [
            prod in g.recursive_prods for prod in valid_productions
        ]  # Are there any  recursive symbols in our expansion?
    ):
        valid_productions = [
            vp for vp in valid_productions if vp in g.recursive_prods
        ]  # If so, then only expand into recursive symbols

    return valid_productions


def expand_node(
    r: Source,
    g: Grammar,
    wrapper: Callable[[Any, str, int, Callable[[int], Any]], Any],
    depth,
    starting_symbol,
    argname: str = "",
    context: Dict[str, Type] = None,
) -> Any:
    """
    Creates a random node of a given type (starting_symbol)
    """
    if context is None:
        context = {}

    if depth < 0:
        raise GeneticEngineError("Recursion Depth reached")
    if depth < g.get_distance_to_terminal(starting_symbol):
        raise GeneticEngineError(
            "There will be no depth sufficient for symbol {} in this grammar (provided: {}, required: {}).".format(
                starting_symbol, depth, g.get_distance_to_terminal(starting_symbol)
            )
        )

    if starting_symbol is int:
        return random_int(r)
    elif starting_symbol is float:
        return random_float(r)
    elif is_generic_list(starting_symbol):
        return random_list(r, g, wrapper, expand_node, depth, starting_symbol)
    elif is_metahandler(starting_symbol):
        return apply_metahandler(
            r, g, wrapper, expand_node, depth, starting_symbol, argname, context
        )
    else:
        if starting_symbol not in g.all_nodes:
            raise GeneticEngineError(f"Symbol {starting_symbol} not in grammar rules.")

        if starting_symbol in g.alternatives:  # Alternatives
            compatible_productions = g.alternatives[starting_symbol]
            valid_productions = filter_choices(g, compatible_productions, depth)
            if not valid_productions:
                raise GeneticEngineError(
                    "No productions for non-terminal node with type: {} in depth {} (minimum required: {}).".format(
                        starting_symbol,
                        depth,
                        str(
                            [
                                (vp, g.distanceToTerminal[vp])
                                for vp in compatible_productions
                            ]
                        ),
                    )
                )
            if any(["weight" in get_gengy(p) for p in valid_productions]):
                weights = [get_gengy(p).get("weight", 1.0) for p in valid_productions]
                rule = r.choice_weighted(valid_productions, weights)
            else:
                rule = r.choice(valid_productions)
            return expand_node(r, g, wrapper, depth, rule)
        else:  # Normal production
            args = get_arguments(starting_symbol)
            obj = starting_symbol(*[None for _ in args])
            context = {argn: argt for (argn, argt) in args}
            for (argn, argt) in args:
                w = wrapper(
                    obj,
                    argn,
                    depth - 1,
                    lambda d: expand_node(r, g, wrapper, d, argt, argn, context),
                )
                setattr(obj, argn, w)
            return obj


@dataclass
class Future(object):
    parent: Any
    name: str
    depth: int
    get: Union[
        Callable[[int], Any], Callable[[int], Any]
    ]  # This is due to mypy bug 708


def extract_futures(obj: Any) -> List[Future]:
    futures = []
    if isinstance(obj, list):
        for el in obj:
            if isinstance(el, Future):
                futures.append(el)
            else:
                futures.extend(extract_futures(el))
    else:
        for (name, ty) in get_arguments(obj):
            v = getattr(obj, name)
            if isinstance(v, Future):
                futures.append(v)
            # Do we want a full recursion here? probably not for performance reasons
            # else:
            #    futures.extend(extract_futures(v))
    return futures


def PI_Grow(
    r: Source,
    g: Grammar,
    depth: int,
    starting_symbol: Type[Any] = int,
):
    def wrapper(parent: Any, name: str, depth: int, callback: Callable[[int], Any]):
        return Future(parent=parent, name=name, depth=depth, get=callback)

    root = expand_node(r, g, wrapper, depth, starting_symbol)
    prod_queue: List[Future] = [root]

    while prod_queue:
        index = r.randint(0, len(prod_queue) - 1)
        future = prod_queue.pop(index)
        if isinstance(future, Future):
            obj = future.get(future.depth)
            setattr(future.parent, future.name, obj)
        else:
            obj = future  # only for root

        prod_queue.extend(extract_futures(obj))

    relabel_nodes_of_trees(root, g.non_terminals)
    return root


random_node = PI_Grow


def random_individual(r: Source, g: Grammar, max_depth: int = 5) -> TreeNode:
    try:
        assert max_depth >= g.get_min_tree_depth()
    except:
        if g.get_min_tree_depth() == 1000000:
            raise GeneticEngineError(
                f"Grammar's minimal tree depth is {g.get_min_tree_depth()}, which is the default tree depth. It's highly like that there are nodes of your grammar than cannot reach any terminal."
            )
        raise GeneticEngineError(
            f"Cannot use complete grammar for individual creation. Max depth ({max_depth}) is smaller than grammar's minimal tree depth ({g.get_min_tree_depth()})."
        )
    ind = random_node(r, g, max_depth, g.starting_symbol)
    assert isinstance(ind, TreeNode)
    return ind


def mutate_inner(r: Source, g: Grammar, i: TreeNode, max_depth: int) -> TreeNode:
    if i.nodes > 0:
        c = r.randint(0, i.nodes - 1)
        if c == 0:
            ty = i.__class__.__bases__[0]
            try:
                replacement = random_node(r, g, max_depth - i.depth + 1, ty)
                return replacement
            except:
                return i
        else:
            for field in i.__annotations__:
                child = getattr(i, field)
                if hasattr(child, "nodes"):
                    count = child.nodes
                    if c <= count:
                        setattr(i, field, mutate_inner(r, g, child, max_depth))
                        return i
                    else:
                        c -= count
            return i
    else:
        return i


def mutate(r: Source, g: Grammar, i: TreeNode, max_depth: int) -> Any:
    new_tree = mutate_inner(r, g, deepcopy(i), max_depth)
    relabeled_new_tree = relabel_nodes_of_trees(new_tree, g.non_terminals)
    return relabeled_new_tree


def find_in_tree(ty: type, o: TreeNode, max_depth: int):
    if ty in o.__class__.__bases__ and o.distance_to_term <= max_depth:
        yield o
    if hasattr(o, "__annotations__"):
        for field in o.__annotations__:
            child = getattr(o, field)
            yield from find_in_tree(ty, child, max_depth)


def tree_crossover_inner(
    r: Source, g: Grammar, i: TreeNode, o: TreeNode, max_depth: int
) -> Any:
    if i.nodes > 0:
        c = r.randint(0, i.nodes - 1)
        if c == 0:
            ty = i.__class__.__bases__[0]
            replacement = None
            options = list(find_in_tree(ty, o, max_depth - i.depth + 1))
            if options:
                replacement = r.choice(options)
            if replacement is None:
                try:
                    replacement = random_node(r, g, max_depth - i.depth + 1, ty)
                except:
                    return i
            return replacement
        else:
            for field in i.__annotations__:
                child = getattr(i, field)
                if hasattr(child, "nodes"):
                    count = getattr(i, field).nodes
                    if c <= count:
                        setattr(
                            i,
                            field,
                            tree_crossover_inner(r, g, getattr(i, field), o, max_depth),
                        )
                        return i
                    else:
                        c -= count
            return i
    else:
        return i


def tree_crossover(
    r: Source, g: Grammar, p1: TreeNode, p2: TreeNode, max_depth: int
) -> Tuple[TreeNode, TreeNode]:
    """
    Given the two input trees [p1] and [p2], the grammar and the random source, this function returns two trees that are created by crossing over [p1] and [p2]. The first tree returned has [p1] as the base, and the second tree has [p2] as a base.
    """
    new_tree1 = tree_crossover_inner(r, g, deepcopy(p1), deepcopy(p2), max_depth)
    relabeled_new_tree1 = relabel_nodes_of_trees(new_tree1, g.non_terminals)
    new_tree2 = tree_crossover_inner(r, g, deepcopy(p2), deepcopy(p1), max_depth)
    relabeled_new_tree2 = relabel_nodes_of_trees(new_tree2, g.non_terminals)
    return relabeled_new_tree1, relabeled_new_tree2


def tree_crossover_single_tree(
    r: Source, g: Grammar, p1: TreeNode, p2: TreeNode, max_depth: int
) -> TreeNode:
    """
    Given the two input trees [p1] and [p2], the grammar and the random source, this function returns one tree that is created by crossing over [p1] and [p2]. The tree returned has [p1] as the base.
    """
    new_tree = tree_crossover_inner(r, g, deepcopy(p1), deepcopy(p2), max_depth)
    relabeled_new_tree = relabel_nodes_of_trees(new_tree, g.non_terminals)
    return relabeled_new_tree


def get_property_names(obj: TreeNode) -> List[Any]:
    if hasattr(obj, "__annotations__"):
        return [field for field in obj.__annotations__]
    else:
        return []


def relabel_nodes_of_trees(
    i: TreeNode, non_terminals: Set[type], max_depth: int = 1
) -> TreeNode:
    """Recomputes all the nodes, depth and distance_to_term in the tree"""

    # print("Node: {}, nodes: {}, distance_to_term: {}, depth: {}.".format(i,i.nodes,i.distance_to_term,i.depth))
    def relabel_nodes(i: TreeNode, depth: int = 1) -> Tuple[int, int]:
        children: List[Any]
        if is_terminal(type(i), non_terminals):
            if not is_builtin(type(i)):
                i.depth = depth
                i.distance_to_term = 1
                i.nodes = 0
            return (0, 1)
        elif isinstance(i, list):
            children = i
        else:
            children = [getattr(i, field) for field in get_property_names(i)]
        assert children
        properties_of_children = [relabel_nodes(child, depth + 1) for child in children]
        number_of_nodes = 1 + sum([prop[0] for prop in properties_of_children])
        distance_to_term = 1 + max([prop[1] for prop in properties_of_children])
        if not isinstance(i, list):
            i.depth = depth
            i.distance_to_term = distance_to_term
            i.nodes = number_of_nodes
        return number_of_nodes, distance_to_term

    # print("Node: {}, nodes: {}, distance_to_term: {}, depth: {}.".format(i,i.nodes,i.distance_to_term,i.depth))
    relabel_nodes(i, max_depth)
    return i


class TreeBasedRepresentation(Representation[TreeNode]):
    def create_individual(self, r: Source, g: Grammar, depth: int) -> TreeNode:
        return random_individual(r, g, depth)

    def mutate_individual(
        self, r: Source, g: Grammar, ind: TreeNode, depth: int
    ) -> TreeNode:
        return mutate(r, g, ind, depth)

    def crossover_individuals(
        self, r: Source, g: Grammar, i1: TreeNode, i2: TreeNode, int
    ) -> Tuple[TreeNode, TreeNode]:
        return tree_crossover(r, g, i1, i2, int)

    def genotype_to_phenotype(self, g: Grammar, genotype: TreeNode) -> TreeNode:
        return genotype


treebased_representation = TreeBasedRepresentation()
