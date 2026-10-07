from difflib import SequenceMatcher


class SemanticMatcher:
    def similarity(self, source: str, target: str) -> float:
        return SequenceMatcher(None, source.lower(), target.lower()).ratio()

    def best_match_score(self, needle: str, haystack: list[str]) -> float:
        if not haystack:
            return 0.0
        return max(self.similarity(needle, item) for item in haystack)
