"""Print the number of entries in each word file and the total."""

from app import BASE_DIR, load_words


def main():
    files = sorted(BASE_DIR.glob("*.txt"))
    if not files:
        print("No word files found.")
        return

    width = max(len(path.name) for path in files)
    total = 0
    for path in files:
        count = len(load_words(path))
        total += count
        print(f"{path.name:<{width}}  {count:>4}")

    print("-" * (width + 6))
    print(f"{'total':<{width}}  {total:>4}")


if __name__ == "__main__":
    main()
