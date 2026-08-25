"""回声工具：从 stdin 读取 JSON 参数，把结果打印到 stdout。"""

import json
import sys


def main():
    args = json.load(sys.stdin)
    print(args["text"])


if __name__ == "__main__":
    main()
