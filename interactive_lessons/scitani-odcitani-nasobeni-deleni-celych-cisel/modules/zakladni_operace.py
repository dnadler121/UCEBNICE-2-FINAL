import random
from typing import List, Union, Dict, Optional

Token = Union[int, str]


def _safe_nonzero(max_number: int) -> int:
    value = 0
    while value == 0:
        value = random.randint(-max_number, max_number)
    return value


def _make_term(number_count: int, mul_ops: List[str], max_number: int) -> List[Token]:
    """Vytvoří násobicí/dělicí člen s celočíselným dělením."""
    if number_count <= 1:
        return [random.randint(-max_number, max_number)]

    current = _safe_nonzero(max_number)
    tokens: List[Token] = [current]

    for _ in range(number_count - 1):
        op = random.choice(mul_ops)
        if op == "*":
            operand = _safe_nonzero(max(3, min(max_number, 12)))
            current *= operand
            tokens.extend(["*", operand])
        else:
            abs_current = abs(current)
            divisors = [
                d for d in range(1, min(abs_current, max_number) + 1)
                if abs_current % d == 0
            ]
            divisor = random.choice(divisors or [1])
            if random.choice([True, False]):
                divisor *= -1
            current //= divisor
            tokens.extend(["/", divisor])

    return tokens


def _generate_without_parentheses(
    number_count: int,
    allowed_operations: List[str],
    max_number: int,
) -> List[Token]:
    add_ops = [op for op in allowed_operations if op in {"+", "-"}]
    mul_ops = [op for op in allowed_operations if op in {"*", "/"}]

    if not mul_ops:
        tokens: List[Token] = [random.randint(-max_number, max_number)]
        for _ in range(number_count - 1):
            tokens.extend([random.choice(add_ops), random.randint(-max_number, max_number)])
        return tokens

    if not add_ops:
        return _make_term(number_count, mul_ops, max_number)

    term_count = random.randint(2, min(3, number_count))
    sizes = [1] * term_count
    remaining = number_count - term_count
    while remaining > 0:
        sizes[random.randrange(term_count)] += 1
        remaining -= 1

    tokens: List[Token] = []
    for i, size in enumerate(sizes):
        if i > 0:
            tokens.append(random.choice(add_ops))
        tokens.extend(_make_term(size, mul_ops, max_number))
    return tokens


def _add_parentheses(tokens: List[Token]) -> List[Token]:
    """Vloží právě jednu dvojici kulatých závorek kolem části výrazu."""
    number_positions = [i for i, token in enumerate(tokens) if isinstance(token, int)]
    count = len(number_positions)
    if count < 2:
        return tokens

    candidates = []
    for start_number in range(count - 1):
        for end_number in range(start_number + 1, min(count, start_number + 3)):
            # Neobalujeme celý příklad – závorky mají skutečně měnit postup.
            if start_number == 0 and end_number == count - 1:
                continue
            start = number_positions[start_number]
            end = number_positions[end_number]
            candidates.append((start, end))

    if not candidates:
        return tokens

    start, end = random.choice(candidates)
    return tokens[:start] + ["("] + tokens[start:end + 1] + [")"] + tokens[end + 1:]


def generate_expression(
    number_count: int = 5,
    allowed_operations: Optional[List[str]] = None,
    max_number: int = 20,
    use_parentheses: bool = True,
) -> List[Token]:
    allowed = allowed_operations or ["+", "-", "*", "/"]

    # Zkoušíme různé příklady, dokud je lze po jednotlivých krocích
    # spočítat pouze v celých číslech.
    for _ in range(300):
        tokens = _generate_without_parentheses(number_count, allowed, max_number)
        if use_parentheses:
            tokens = _add_parentheses(tokens)
        if _is_valid_expression(tokens):
            return tokens

    # Bezpečná záloha pro mimořádně nešťastné náhodné kombinace.
    return [12, "-", "(", 8, "-", 3, ")", "+", 2]


def _calculate(a: int, op: str, b: int) -> int:
    if op == "+":
        return a + b
    if op == "-":
        return a - b
    if op == "*":
        return a * b
    if op == "/":
        if b == 0 or a % b != 0:
            raise ValueError("Dělení musí mít celočíselný výsledek.")
        return a // b
    raise ValueError("Neznámá operace.")


def _innermost_range(tokens: List[Token]) -> Optional[tuple[int, int]]:
    stack: List[int] = []
    for i, token in enumerate(tokens):
        if token == "(":
            stack.append(i)
        elif token == ")":
            if not stack:
                raise ValueError("Chybně zapsané závorky.")
            return stack.pop(), i
    if stack:
        raise ValueError("Chybně zapsané závorky.")
    return None


def _operation_in_range(tokens: List[Token], start: int, end: int) -> Optional[Dict]:
    for priorities in ({"*", "/"}, {"+", "-"}):
        for i in range(start + 1, end):
            if tokens[i] in priorities:
                if i - 1 < start or i + 1 >= end:
                    continue
                if not isinstance(tokens[i - 1], int) or not isinstance(tokens[i + 1], int):
                    continue
                a = int(tokens[i - 1])
                op = str(tokens[i])
                b = int(tokens[i + 1])
                return {
                    "index": i,
                    "left": a,
                    "operator": op,
                    "right": b,
                    "result": _calculate(a, op, b),
                    "in_parentheses": start > -1,
                }
    return None


def next_operation(tokens: List[Token]) -> Optional[Dict]:
    tokens = _remove_redundant_parentheses(tokens)
    if len(tokens) == 1:
        return None

    inner = _innermost_range(tokens)
    if inner is not None:
        left_paren, right_paren = inner
        operation = _operation_in_range(tokens, left_paren, right_paren)
        if operation:
            return operation

    # Mimo závorky vybíráme jen operace v hloubce 0.
    depth = 0
    for priorities in ({"*", "/"}, {"+", "-"}):
        depth = 0
        for i, token in enumerate(tokens):
            if token == "(":
                depth += 1
            elif token == ")":
                depth -= 1
            elif depth == 0 and token in priorities:
                if i > 0 and i + 1 < len(tokens) and isinstance(tokens[i - 1], int) and isinstance(tokens[i + 1], int):
                    a = int(tokens[i - 1])
                    op = str(token)
                    b = int(tokens[i + 1])
                    return {
                        "index": i,
                        "left": a,
                        "operator": op,
                        "right": b,
                        "result": _calculate(a, op, b),
                        "in_parentheses": False,
                    }
    return None


def _remove_redundant_parentheses(tokens: List[Token]) -> List[Token]:
    result = list(tokens)
    changed = True
    while changed:
        changed = False
        for i in range(len(result) - 2):
            if result[i] == "(" and isinstance(result[i + 1], int) and result[i + 2] == ")":
                result = result[:i] + [result[i + 1]] + result[i + 3:]
                changed = True
                break
    return result


def apply_step(tokens: List[Token], operator_index: int) -> List[Token]:
    a = int(tokens[operator_index - 1])
    op = str(tokens[operator_index])
    b = int(tokens[operator_index + 1])
    result = _calculate(a, op, b)
    new_tokens = tokens[:operator_index - 1] + [result] + tokens[operator_index + 2:]
    return _remove_redundant_parentheses(new_tokens)


def _is_valid_expression(tokens: List[Token]) -> bool:
    try:
        work = list(tokens)
        for _ in range(100):
            work = _remove_redundant_parentheses(work)
            operation = next_operation(work)
            if operation is None:
                return len(work) == 1 and isinstance(work[0], int)
            work = apply_step(work, operation["index"])
        return False
    except (ValueError, ZeroDivisionError, IndexError):
        return False


def _number_html(value: int) -> str:
    return f"({value})" if value < 0 else str(value)


def format_expression(tokens: List[Token]) -> str:
    tokens = _remove_redundant_parentheses(tokens)
    active = next_operation(tokens)
    active_index = active["index"] if active else None

    parts = []
    for i, token in enumerate(tokens):
        if isinstance(token, int):
            text = _number_html(token)
        else:
            symbols = {"*": "·", "/": ":", "+": "+", "-": "−", "(": "(", ")": ")"}
            text = symbols[token]

        if active_index is not None and i in {active_index - 1, active_index, active_index + 1}:
            parts.append(f'<span class="active-part">{text}</span>')
        elif token in {"(", ")"}:
            parts.append(f'<span class="parenthesis">{text}</span>')
        else:
            parts.append(f"<span>{text}</span>")

    return " ".join(parts)
