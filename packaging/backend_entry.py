"""Execute the existing backend module with package-relative imports intact."""

import runpy


def main() -> None:
    runpy.run_module("backend.main", run_name="__main__", alter_sys=True)


if __name__ == "__main__":
    main()
