import difflib

def compare_text_files(file1_path, file2_path):
    with open(file1_path, 'r') as file1, open(file2_path, 'r') as file2:
        text1 = file1.readlines()
        text2 = file2.readlines()

    diff = difflib.unified_diff(text1, text2, fromfile=file1_path, tofile=file2_path)

    for line in diff:
        print(line)

# Usage example
file1_path = 'file1.txt'
file2_path = 'file2.txt'
compare_text_files(file1_path, file2_path)
