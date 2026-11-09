import os


def get_all_files(root_folder):
    all_files = []
    for dirpath, _, filenames in os.walk(root_folder):
        for filename in filenames:
            full_path = os.path.join(dirpath, filename)
            all_files.append(full_path)
    return all_files

def compare_files(file1, file2):
    """Compara o conteudo de dois arquivos, byte a byte.

    Nao usa `filecmp.cmp`: o cache interno dele e indexado por
    `(mode, st_size, st_mtime)` - dois arquivos com mesmo tamanho e mesma marca
    de tempo devolvem o resultado da comparacao anterior. Num verificador de
    espelho isso e exatamente o falso positivo perigoso: um arquivo corrompido
    que manteve o tamanho seria dado como igual.

    Returns:
        bool: True se os conteudos sao identicos.
    """
    try:
        with open(file1, "rb") as fa, open(file2, "rb") as fb:
            while True:
                a = fa.read(65536)
                b = fb.read(65536)
                if a != b:
                    return False
                if not a:
                    return True
    except OSError:
        return False

def compare_folders(folder1, folder2):
    folder1_files = get_all_files(folder1)
    folder2_files = get_all_files(folder2)
    
    folder1_relative_paths = [os.path.relpath(file, folder1) for file in folder1_files]
    folder2_relative_paths = [os.path.relpath(file, folder2) for file in folder2_files]
    
    common_files = set(folder1_relative_paths).intersection(folder2_relative_paths)
    
    discrepancies = []
    
    for relative_path in common_files:
        file1 = os.path.join(folder1, relative_path)
        file2 = os.path.join(folder2, relative_path)
        
        if not compare_files(file1, file2):
            discrepancies.append(relative_path)
    
    unique_to_folder1 = set(folder1_relative_paths) - set(folder2_relative_paths)
    unique_to_folder2 = set(folder2_relative_paths) - set(folder1_relative_paths)
    
    return discrepancies, unique_to_folder1, unique_to_folder2

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("usage: verify_mirror.py <folder1> <folder2>")
        sys.exit(1)
    folder1, folder2 = sys.argv[1], sys.argv[2]
    
    discrepancies, unique_to_folder1, unique_to_folder2 = compare_folders(folder1, folder2)
    
    if not discrepancies and not unique_to_folder1 and not unique_to_folder2:
        print("The folders are identical.")
    else:
        if discrepancies:
            print("Files that differ between the two folders:")
            for discrepancy in discrepancies:
                print(discrepancy)
        
        if unique_to_folder1:
            print("Files unique to folder1:")
            for unique_file in unique_to_folder1:
                print(unique_file)
        
        if unique_to_folder2:
            print("Files unique to folder2:")
            for unique_file in unique_to_folder2:
                print(unique_file)