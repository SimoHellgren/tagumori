import sys

from lark.tools.standalone import main

GRAMMAR_FILE = "tagumori/query/grammar.lark"
OUTPUT_FILE = "tagumori/query/parser.py"

if __name__ == "__main__":
    sys.argv = [
        "lark-standalone",
        GRAMMAR_FILE,
        "-o",
        OUTPUT_FILE,
    ]

    main()
    print(f"Wrote standalone parser to {OUTPUT_FILE}")
