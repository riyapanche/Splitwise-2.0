"""Business objects for the Splitwise-style receipt splitting domain."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


def _to_cents(amount: float) -> int:
    return int(round(float(amount) * 100))


def _from_cents(cents: int) -> float:
    return round(cents / 100, 2)


@dataclass
class Split:
    """Represents how much one person owes for a single item."""

    user_id: str
    amount: float

    def __post_init__(self) -> None:
        self.amount = round(float(self.amount), 2)

    def to_dict(self) -> dict[str, object]:
        return {"userID": self.user_id, "amount": self.amount}


class SplitStrategy(ABC):
    """Base class for all split strategies."""

    @abstractmethod
    def calc_split(self, amount: float, user_ids: list[str], values: Optional[list[float]] = None) -> list[Split]:
        """Return a list of Split objects whose total equals the provided amount."""
        raise NotImplementedError


class EqualSplit(SplitStrategy):
    """Split an amount evenly across the selected users."""

    def calc_split(self, amount: float, user_ids: list[str], values: Optional[list[float]] = None) -> list[Split]:
        if not user_ids:
            return []

        total_cents = _to_cents(amount)
        base_cents, remainder_cents = divmod(total_cents, len(user_ids))

        shares = [base_cents] * len(user_ids)
        if remainder_cents:
            shares[-1] += remainder_cents

        return [Split(user_id, _from_cents(share_cents)) for user_id, share_cents in zip(user_ids, shares)]


class PercentSplit(SplitStrategy):
    """Split by percentages that should sum to 100%."""

    def calc_split(self, amount: float, user_ids: list[str], values: Optional[list[float]] = None) -> list[Split]:
        if not values or len(values) != len(user_ids):
            raise ValueError("Values must be provided and match the number of user IDs.")

        if round(sum(values), 2) != 100:
            raise ValueError("The sum of percentage values must equal 100.")

        total_cents = _to_cents(amount)
        share_cents = []
        running_total = 0

        for pct in values:
            raw_cents = int(round(total_cents * (pct / 100)))
            share_cents.append(raw_cents)
            running_total += raw_cents

        leftover_cents = total_cents - running_total
        if leftover_cents and share_cents:
            share_cents[-1] += leftover_cents

        return [Split(user_id, _from_cents(cents)) for user_id, cents in zip(user_ids, share_cents)]


class ExactSplit(SplitStrategy):
    """Split by exact dollar amounts that should sum to the item price."""

    def calc_split(self, amount: float, user_ids: list[str], values: Optional[list[float]] = None) -> list[Split]:
        if not values or len(values) != len(user_ids):
            raise ValueError("Values must be provided and match the number of user IDs.")

        target_cents = _to_cents(amount)
        provided_cents = sum(_to_cents(value) for value in values)

        if provided_cents != target_cents:
            raise ValueError("The sum of exact values must equal the item amount.")

        return [Split(user_id, round(float(value), 2)) for user_id, value in zip(user_ids, values)]


class SplitType:
    EQUAL = "EQUAL"
    PERCENTAGE = "PERCENTAGE"
    EXACT = "EXACT"


class SplitFactory:
    """Factory that creates the appropriate split strategy for a split type."""

    @staticmethod
    def create_split_strategy(split_type: str) -> SplitStrategy:
        if split_type == SplitType.EQUAL:
            return EqualSplit()
        if split_type == SplitType.PERCENTAGE:
            return PercentSplit()
        if split_type == SplitType.EXACT:
            return ExactSplit()
        raise ValueError(f"Unknown split type: {split_type}")


class Observer(ABC):
    """Simple observer interface for user notifications."""

    @abstractmethod
    def update(self, msg: str) -> None:
        raise NotImplementedError


@dataclass
class User(Observer):
    """Represents a person participating in a group or expense."""

    id: str
    name: str
    email: str = ""
    balance: dict[str, float] = field(default_factory=dict)

    def update(self, msg: str) -> None:
        print(f"{self.name}: {msg}")


@dataclass
class Expense:
    """Represents one expense tied to a group and a set of splits."""

    expense_id: str
    desc: str
    amount: float
    paid_user_id: str
    splits: list[Split] = field(default_factory=list)
    group_id: Optional[str] = None


class Group:
    """A collection of users and expenses with balance tracking."""

    def __init__(self, group_id: str, name: str):
        self.group_id = group_id
        self.name = name
        self.users: list[User] = []
        self.balance: dict[str, dict[str, float]] = {}
        self.expenses: dict[str, Expense] = {}

    def add_user(self, user: User) -> None:
        if user not in self.users:
            self.users.append(user)
            self.balance[user.id] = {}

    def remove_user(self, user: User) -> None:
        if user in self.users:
            self.users.remove(user)
            self.balance.pop(user.id, None)

    def notify(self, msg: str) -> None:
        for user in self.users:
            user.update(msg)

    def add_expense(self, expense: Expense) -> None:
        self.expenses[expense.expense_id] = expense
        self.notify(f"Added expense {expense.desc}")

    def update_balance(self, from_user_id: str, to_user_id: str, amt: float) -> None:
        self.balance.setdefault(from_user_id, {})[to_user_id] = round(
            self.balance.setdefault(from_user_id, {}).get(to_user_id, 0.0) + amt,
            2,
        )
        self.balance.setdefault(to_user_id, {})[from_user_id] = round(
            self.balance.setdefault(to_user_id, {}).get(from_user_id, 0.0) - amt,
            2,
        )

    def settle_payment(self, from_user_id: str, to_user_id: str, amt: float) -> None:
        self.update_balance(from_user_id, to_user_id, amt)

    def simplify_transactions(self) -> list[tuple[str, str, float]]:
        simplified: list[tuple[str, str, float]] = []
        for from_id, peers in self.balance.items():
            for to_id, amount in peers.items():
                if amount:
                    simplified.append((from_id, to_id, round(amount, 2)))
        return simplified


class Splitwise:
    """Top-level manager for users, groups, and expenses."""

    def __init__(self) -> None:
        self.users: dict[str, User] = {}
        self.groups: dict[str, Group] = {}
        self.expenses: dict[str, Expense] = {}

    def settle_individual_payment(self, from_user_id: str, to_user_id: str, amt: float) -> None:
        self.users.setdefault(from_user_id, User(from_user_id, ""))
        self.users.setdefault(to_user_id, User(to_user_id, ""))
        if not self.groups:
            return
        first_group = next(iter(self.groups.values()))
        first_group.settle_payment(from_user_id, to_user_id, amt)

    def add_individual_expense(self, expense: Expense) -> None:
        self.expenses[expense.expense_id] = expense


def _run_smoke_tests() -> None:
    equal_splits = EqualSplit().calc_split(10.00, ["Alice", "Bob", "Carol"])
    assert [split.amount for split in equal_splits] == [3.33, 3.33, 3.34]
    assert round(sum(split.amount for split in equal_splits), 2) == 10.00

    percent_splits = PercentSplit().calc_split(10.00, ["Alice", "Bob", "Carol"], [33.33, 33.33, 33.34])
    assert [split.amount for split in percent_splits] == [3.33, 3.33, 3.34]
    assert round(sum(split.amount for split in percent_splits), 2) == 10.00

    exact_splits = ExactSplit().calc_split(10.00, ["Alice", "Bob", "Carol"], [2.5, 2.5, 5.0])
    assert [split.amount for split in exact_splits] == [2.5, 2.5, 5.0]
    assert round(sum(split.amount for split in exact_splits), 2) == 10.00

    factory_strategy = SplitFactory.create_split_strategy(SplitType.EQUAL)
    assert isinstance(factory_strategy, EqualSplit)


if __name__ == "__main__":
    _run_smoke_tests()
    print("Smoke tests passed")