import csv
import re


INPUT_FILE_NAME = "tools/last_names.txt"
OUTPUT_FILE_NAME = "tools/last_names.csv"


def transform_line(raw_line):
    stripped_line = raw_line.strip()
    if not stripped_line:
        return None

    columns = re.split(r"\s+", stripped_line)
    if len(columns) < 4:
        return None

    last_name = columns[0]
    percentage_value = float(columns[2].replace(",", ""))
    weight = int(round(percentage_value * 1000))

    return ["name", "last_name", last_name, weight]


def main():
    with open(INPUT_FILE_NAME, "r", encoding="utf-8") as input_file, open(
        OUTPUT_FILE_NAME, "w", encoding="utf-8", newline=""
    ) as output_file:
        csv_writer = csv.writer(output_file)

        csv_writer.writerow(["trait_group", "trait_name", "option", "weight"])

        for raw_line in input_file:
            transformed_row = transform_line(raw_line)
            if transformed_row is not None:
                csv_writer.writerow(transformed_row)


if __name__ == "__main__":
    main()