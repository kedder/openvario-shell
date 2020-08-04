def format_size(size: int) -> str:
    fsize = float(size)
    # make suffix the same size to keep numbers dot-aligned
    for unit in ["B  ", "KiB", "MiB", "GiB"]:
        if abs(fsize) < 1024.0:
            return "%3.1f %s" % (fsize, unit)
        fsize /= 1024.0
    return "%.1f %s" % (fsize, "TiB")
