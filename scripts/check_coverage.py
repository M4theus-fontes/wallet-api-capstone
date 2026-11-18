"""Valida linhas e branches separadamente, sem arredondar antes da comparação."""
import sys
from xml.etree import ElementTree


def main(path):
    root = ElementTree.parse(path).getroot()
    lines_hit = int(root.attrib["lines-covered"])
    lines_total = int(root.attrib["lines-valid"])
    branches_hit = int(root.attrib["branches-covered"])
    branches_total = int(root.attrib["branches-valid"])
    if not lines_total or not branches_total:
        print("Relatório sem linhas ou branches instrumentados.")
        return 1
    print(f"Linhas: {lines_hit}/{lines_total} ({lines_hit / lines_total:.2%}), mínimo 85%")
    print(f"Branches: {branches_hit}/{branches_total} ({branches_hit / branches_total:.2%}), mínimo 80%")
    return int(lines_hit * 100 < 85 * lines_total or branches_hit * 100 < 80 * branches_total)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
