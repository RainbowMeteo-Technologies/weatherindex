

def precision(true_positive: int, false_positive: int) -> float:
    sum = true_positive + false_positive
    if sum == 0:
        return 0.0

    return true_positive / sum


def recall(true_positive: int, false_negative: int) -> float:
    sum = true_positive + false_negative
    if sum == 0:
        return 0.0

    return true_positive / sum


def fscore(precision: float, recall: float) -> float:
    if (precision + recall) == 0.0:
        return 0.0

    return 2 * (precision * recall) / (precision + recall)
