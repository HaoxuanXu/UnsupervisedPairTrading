

def deserializePairData(data:dict[str, float]) -> dict[tuple, float]:
    return {(pair.split(",")[0], pair.split(",")[1]):zscore
                                 for pair, zscore in data.items()}  


def serializePairData(data:dict[tuple, float]) -> dict[str, float]:
    return {",".join(list(key)):zscore for key, zscore in data.items()}