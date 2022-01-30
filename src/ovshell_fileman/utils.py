def format_size(size: int) -> str:
    fsize = float(size)
    # make suffix the same size to keep numbers dot-aligned
    for unit in ["B  ", "KiB", "MiB", "GiB"]:
        if abs(fsize) < 1024.0:
            return f"{fsize:3.1f} {unit}"
        fsize /= 1024.0
    return "{:.1f} {}".format(fsize, "TiB")
