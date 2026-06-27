
def validate_matrix(matrix) -> bool:
    return (
        isinstance(matrix, list) and
        len(matrix) > 0 and
        all(
            isinstance(row, list) and
            all(isinstance(cell, int) for cell in row)
            for row in matrix
        )
    ) 