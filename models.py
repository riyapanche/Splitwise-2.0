"""
Implements the split strategy for the design.
"""

from abc import ABC, abstractmethod

class Split:
    """
    Represents how much one person owes for one item.
    """

    def __init__(self, user_id: str, amount: float):
        self.user_id = user_id
        self.amount = round(amount, 2)

    def to_dict(self):
        return {"userID": self.user_id, "amount": self.amount}
    
    def __repr__(self):
        return f"Split(user_id={self.user_id}, amount={self.amount})"
    
class SplitStrategy(ABC):
    """
    Abstract base class for split strategies.
    """

    @abstractmethod
    def calc_split(self, amount: float, user_ids: list[str]) -> list[Split]:
        """
        Splits the amount among the given user IDs.

        Args:
            amount (float): The amount to be split.
            user_ids (list[str]): A list of user IDs among whom the amount will be split.

        Returns:
            list[Split]: A list of Split objects representing how much each user owes.
        """
        raise NotImplementedError
    
class EqualSplit(SplitStrategy):
    """
    Implements the equal split strategy.
    """

    def calc_split(self, amount: float, user_ids: list[str], values=None) -> list[Split]:
        if not user_ids:
            return []
        
        n = len(user_ids)
        share = round(amount / n, 2)
        splits = [Split(user_id, share) for user_id in user_ids]

        total_assigned = round(share * n, 2)
        leftover = round(amount - total_assigned, 2)
        if leftover != 0:
            splits[-1].amount = round(splits[-1].amount + leftover, 2)
        
        return splits
    
class PercentSplit(SplitStrategy):
    def calc_split(self, amount: float, user_ids: list[str], values=None) -> list[Split]:
        if not values or len(values) != len(user_ids):
            raise ValueError("Values must be provided and match the number of user IDs.")
        
        if round(sum(values), 2) != 100:
            raise ValueError("The sum of percentage values must equal 100.")
        
        splits = [
            Split(user_id, amount * (pct / 100))
            for user_id, pct in zip(user_ids, values)
        ]

        total_assigned = round(sum(s.amount for s in splits), 2)
        leftover = round(amount - total_assigned, 2)
        if leftover != 0 and splits:
            splits[-1].amount = round(splits[-1].amount + leftover, 2)

        return splits
    
class ExactSplit(SplitStrategy):
    def calc_split(self, amount: float, user_ids: list[str], values=None) -> list[Split]:
        if not values or len(values) != len(user_ids):
            raise ValueError("Values must be provided and match the number of user IDs.")
        
        total = round(sum(values), 2)
        if total != round(amount, 2):
            raise ValueError(f"The sum of exact values must equal ${total} amount.")
        
        return [Split(user_id, value) for user_id, value in zip(user_ids, values)]
        
class SplitType:
    EQUAL = "EQUAL"
    PERCENT = "PERCENT"
    EXACT = "EXACT"

class SplitFactory:
    @staticmethod
    def create_split_strategy(split_type):
        if split_type == SplitType.EQUAL:
            return EqualSplit()
        elif split_type == SplitType.PERCENT:
            return PercentSplit()
        elif split_type == SplitType.EXACT:
            return ExactSplit()
        else:
            raise ValueError(f"Unknown split type: {split_type}")