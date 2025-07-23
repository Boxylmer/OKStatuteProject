def match_string_prefix_fuzzy(body: str, prefix: str) -> int | None:
    """
    Find the line-up index of a prefix in a body of text, ignoring whitespace, newlines, etc.
    The index returned is the ending position of the prefix string for the *body* text.
    E.g.,
    Body: " The
            quick brow
            n fox jumped over the lazy dog"
    Target: "the quick brown
    Result: 15

    """
    b_idx = 0
    p_idx = 0

    def normalize(c):
        return c.lower() if c.isalnum() else None

    while b_idx < len(body) and p_idx < len(prefix):
        # Skip whitespace in body
        if body[b_idx].isspace():
            b_idx += 1
            continue

        # Skip whitespace in prefix
        if prefix[p_idx].isspace():
            p_idx += 1
            continue

        # Skip non-alphanumerics in both
        b_char = normalize(body[b_idx])
        while b_char is None and b_idx < len(body):
            b_idx += 1
            if b_idx < len(body):
                b_char = normalize(body[b_idx])

        p_char = normalize(prefix[p_idx])
        while p_char is None and p_idx < len(prefix):
            p_idx += 1
            if p_idx < len(prefix):
                p_char = normalize(prefix[p_idx])

        # If either index is now out of range, break
        if p_idx >= len(prefix):
            break
        if b_idx >= len(body):
            break

        # Compare normalized characters
        if b_char != p_char:
            return None

        # Advance
        b_idx += 1
        p_idx += 1

    # Confirm full prefix consumed
    while p_idx < len(prefix):
        if normalize(prefix[p_idx]) is not None:
            return None
        p_idx += 1

    return b_idx  # prefix / body had total line-up, # TODO maybe another error or just return an empty string? Not sure yet.

    # TODO: Not sure what I should be doing to make this more readable. Kind of bog standard fuzzy string matching logic, but very much not pythonic.
